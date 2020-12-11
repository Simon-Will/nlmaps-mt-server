from flask import current_app, jsonify, request

from joeynmt_server.joey_model import JoeyModel
from joeynmt_server.models import Feedback, Parse, TrainUsage
from joeynmt_server.utils.batching import (make_dataset, merge_iterators,
                                           MyBucketIterator)


def make_dataset_from_feedback(feedback, model):
    src = []
    trg = []
    for piece in feedback:
        if piece.correct_lin:
            src.append(piece.nl)
            trg.append(piece.correct_lin)

    dataset = make_dataset(src=src, src_field=model.src_field,
                           trg=trg, trg_field=model.trg_field)
    return dataset


@current_app.route('/train', methods=['POST'])
def train():
    segment_1_threshold = 5
    segment_1_batch_size = 5
    segment_2_batch_size = 5
    segment_3_batch_size = 5

    data = request.json
    config_basename = data.get('model')

    joey_dir = current_app.config.get('JOEY_DIR')
    config_file = joey_dir / 'configs' / config_basename
    use_cuda = current_app.config.get('USE_CUDA_TRAIN')
    model = JoeyModel.from_config_file(config_file, joey_dir,
                                       use_cuda=use_cuda)

    feedback = Feedback.query.all()
    segment_1 = []
    segment_2 = []
    smallest_usage_count = segment_1_threshold
    for piece in feedback:
        usage_count = piece.get_usage_count_for_model(config_basename)
        smallest_usage_count = min(smallest_usage_count, usage_count)
        if usage_count <= segment_1_threshold:
            segment_1.append(piece)
        else:
            segment_2.append(piece)

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
        segment_2_iterator = MyBucketIterator(
            dataset=make_dataset_from_feedback(segment_2, model),
            batch_size=segment_2_batch_size, batch_size_fn=batch_size_fn,
            repeat=True, sort_within_batch=True, train=True,
            sort_key=lambda x: len(x.src)
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

    model.train(train_iterator)

    return jsonify({'success': True})
