import logging
import time

from flask import current_app

from joeynmt_server.app import db
from joeynmt_server.joey_model import JoeyModel
from joeynmt_server.models import (EvaluationResult, Feedback, Lock, Parse,
                                   TrainUsage)
from joeynmt_server.utils.batching import (make_dataset, merge_iterators,
                                           MyBucketIterator)
from joeynmt_server.utils.helper import get_utc_now


def make_dataset_from_feedback(feedback, model):
    src = []
    trg = []
    ids = []
    for piece in feedback:
        if piece.correct_lin:
            src.append(piece.nl)
            trg.append(piece.correct_lin)
            ids.append(piece.id)

    dataset = make_dataset(src=src, src_field=model.src_field,
                           trg=trg, trg_field=model.trg_field,
                           ids=ids)
    return dataset


def train(config_basename, smallest_usage_count, segment_1, segment_2):
    segment_1_threshold = 5
    segment_1_batch_size = 5
    segment_2_batch_size = 5
    segment_3_batch_size = 10

    joey_dir = current_app.config.get('JOEY_DIR')
    config_file = joey_dir / 'configs' / config_basename
    use_cuda = current_app.config.get('USE_CUDA_TRAIN')
    model = JoeyModel.from_config_file(config_file, joey_dir,
                                       use_cuda=use_cuda)

    max_epochs = segment_1_threshold - smallest_usage_count
    batch_size_fn = model.get_batch_size_fn()

    iterators = []
    if segment_1:
        segment_1_iterator = MyBucketIterator(
            dataset=make_dataset_from_feedback(segment_1, model),
            batch_size=segment_1_batch_size, batch_size_fn=batch_size_fn,
            max_epochs=max_epochs, repeat=True, sort_within_batch=True,
            train=True, sort_key=lambda x: len(x.src)
        )
        iterators.append(segment_1_iterator)

    if segment_2:
        max_epochs_2 = None if segment_1 else 1
        segment_2_iterator = MyBucketIterator(
            dataset=make_dataset_from_feedback(segment_2, model),
            batch_size=segment_2_batch_size, batch_size_fn=batch_size_fn,
            max_epochs=max_epochs_2, repeat=True, sort_within_batch=True,
            train=True, sort_key=lambda x: len(x.src)
        )
        iterators.append(segment_2_iterator)

    segment_3_iterator = MyBucketIterator(
        dataset=model.train_dataset,
        batch_size=segment_3_batch_size, batch_size_fn=batch_size_fn,
        repeat=True, sort_within_batch=True, train=True,
        sort_key=lambda x: len(x.src)
    )
    iterators.append(segment_3_iterator)

    train_iterator = merge_iterators(*iterators)

    def increment_train_usages(batch):
        ids = {int(id_) for id_ in batch.id if id_ >= 0}
        existing_usages = {
            usage.feedback_id: usage
            for usage in TrainUsage.query.filter(
                TrainUsage.model == config_basename,
                TrainUsage.feedback_id.in_(ids))
        }
        for usage in existing_usages.values():
            usage.usage_count += 1

        ids.difference_update(existing_usages)
        for id_ in ids:
            usage = TrainUsage(
                feedback_id=id_, model=config_basename,
                usage_count=1
            )
            db.session.add(usage)

        db.session.commit()

    model.train(train_iterator, batch_callback=increment_train_usages)

    return model


def get_feedback_segments(config_basename):
    segment_1_threshold = 5
    feedback = Feedback.query.all()
    train_segment_1 = []
    train_segment_2 = []
    dev = []
    test = []
    smallest_usage_count = None
    for piece in feedback:
        if not piece.correct_lin:
            continue

        if piece.split == 'train':
            usage_count = piece.get_usage_count_for_model(config_basename)
            if smallest_usage_count is None:
                smallest_usage_count = usage_count
            else:
                smallest_usage_count = min(smallest_usage_count, usage_count)

            if usage_count < segment_1_threshold:
                train_segment_1.append(piece)
            else:
                train_segment_2.append(piece)
        elif piece.split == 'dev':
            dev.append(piece)
        elif piece.split == 'test':
            test.append(piece)
    return smallest_usage_count, train_segment_1, train_segment_2, dev, test


def acquire_train_lock():
    lock = Lock.query.filter_by(name='train').first()
    considered_expired_timespan = 60 * 60 * 6
    now = get_utc_now(aware=False)
    if lock:
        if (now - lock.created).total_seconds() < considered_expired_timespan:
            return None
        lock.created = now
    else:
        lock = Lock(name='train')
    db.session.add(lock)
    db.session.commit()
    return lock


def train_n_rounds(config_basename, min_rounds=10):
    lock = acquire_train_lock()
    if not lock:
        logging.debug('Did not acquire lock.')
        return

    model = None
    try:
        (smallest_usage_count, train1, train2, dev, _
         ) = get_feedback_segments(config_basename)
        nl_queries_to_reevaluate = {piece.nl for piece in train1}
        logging.info('Training with {} feedback pieces in segment 1'
                     ' and {} pieces in segment 2.'
                     .format(len(train1), len(train2)))
        rounds = 0
        while train1 or (min_rounds and rounds < min_rounds):
            logging.debug('Smallest usage_count: {}. segment_1: {} '
                          .format(smallest_usage_count, train1))
            model = train(config_basename, smallest_usage_count, train1,
                          train2)

            if dev:
                dev_set = make_dataset_from_feedback(dev, model)
                logging.info('Validating on {} feedback pieces.'
                             .format(len(dev_set)))
                results = model.validate(dev_set)
                accuracy = results['score'] / 100
                total = len(dev_set)
                correct = round(accuracy * total)
                logging.info('Got validation result: {}/{} = {}.'
                             .format(correct, total, accuracy))
                evr = EvaluationResult(
                    label='running_dev', model=config_basename,
                    correct=correct, total=total
                )
                db.session.add(evr)
                db.session.commit()
                logging.info('Saving parses from running dev set.')
                for nl, lin in zip(results['sources'], results['hypotheses']):
                    Parse.ensure(nl=nl, model=config_basename, lin=lin)

            rounds += 1
            (smallest_usage_count, train1, train2, dev, _
             ) = get_feedback_segments(config_basename)
            nl_queries_to_reevaluate.update({piece.nl for piece in train1})
    except:
        logging.error('Training failed. Deleting lock.')
        db.session.delete(lock)
        db.session.commit()
        raise

    if model:
        try:
            logging.info('Reevaluating model {} on {} pieces of feedback.'
                .format(config_basename, len(nl_queries_to_reevaluate)))
            lin_queries = model.translate(nl_queries_to_reevaluate)
            for nl, lin in zip(nl_queries_to_reevaluate, lin_queries):
                Parse.ensure(nl=nl, model=config_basename, lin=lin)
            logging.info('Finished reevaluating.')
        except:
            logging.error('Reevaluating model failed. Deleting lock.')
            db.session.delete(lock)
            db.session.commit()
            raise

    db.session.delete(lock)
    db.session.commit()


def train_until_finished(config_basename):
    return train_n_rounds(config_basename, min_rounds=None)


def validate(config_basename, dataset_name='dev'):
    joey_dir = current_app.config.get('JOEY_DIR')
    config_file = joey_dir / 'configs' / config_basename
    use_cuda_train = current_app.config.get('USE_CUDA_TRAIN', False)
    use_cuda = current_app.config.get('USE_CUDA_DEV', use_cuda_train)

    lock = acquire_train_lock()
    while not lock:
        logging.debug('Did not acquire lock. Waiting for a minute.')
        time.sleep(60)

    try:
        model = JoeyModel.from_config_file(config_file, joey_dir,
                                           use_cuda=use_cuda)
        dev_set = model.get_config_dataset(dataset_name)
        if not dev_set:
            msg = 'No such dataset: {}'.format(dataset_name)
            logging.error(msg)
            raise ValueError(msg)

        logging.info('Validating on dataset {}.'.format(dataset_name))
        results = model.validate(dev_set)
        accuracy = results['score'] / 100
        total = len(dev_set)
        correct = round(accuracy * total)
        logging.info('Got validation result: {}/{} = {}.'
                     .format(correct, total, accuracy))
        evr = EvaluationResult(label=dataset_name, model=config_basename,
                               correct=correct, total=total)
        db.session.add(evr)
        db.session.commit()
    except:
        logging.error('Validating failed. Deleting lock.')
        db.session.delete(lock)
        db.session.commit()
        raise

    db.session.delete(lock)
    db.session.commit()
