import logging
import os.path

from torchtext.data import Dataset, Example, Field
from torchtext.datasets import TranslationDataset

from joeynmt.constants import BOS_TOKEN, EOS_TOKEN, PAD_TOKEN, UNK_TOKEN
from joeynmt.batch import Batch
from joeynmt.data import MonoDataset, token_batch_size_fn
from joeynmt.helpers import (load_config, get_latest_checkpoint,
                             load_checkpoint)
from joeynmt.model import build_model
from joeynmt.prediction import parse_test_args, validate_on_data
from joeynmt.training import TrainManager
from joeynmt.vocabulary import Vocabulary

from joeynmt_server.utils.batching import ID_FIELD, make_dataset


def _resolve_path(path, root):
    if not os.path.isabs(path):
        path = os.path.join(root, path)
    return path


def make_config_absolute(config, root):
    section_to_keys = {
        'data': ('train', 'train2', 'dev', 'dev2', 'test', 'src_vocab',
                'trg_vocab'),
        'training': ('model_dir', 'load_model'),
    }
    for section, keys in section_to_keys.items():
        sec = config[section]
        for key in keys:
            if key in sec:
                sec[key] = _resolve_path(sec[key], root)
    return config


class JoeyModel:

    def __init__(self, config, model, train_manager, src_field, trg_field,
                 test_args, joey_dir):
        self.config = config
        self.model = model
        self.train_manager = train_manager
        self.src_field = src_field
        self.trg_field = trg_field
        self.test_args = test_args
        self.joey_dir = joey_dir

        self._train_dataset = None

    @classmethod
    def from_config_file(cls, config_file, joey_dir, use_cuda=None):
        config = make_config_absolute(load_config(config_file), joey_dir)
        if use_cuda is not None:
            config['training']['use_cuda'] = use_cuda

        model_dir = config['training']['model_dir']

        src_vocab_file = config['data'].get(
            'src_vocab', os.path.join(model_dir, 'src_vocab.txt')
        )
        trg_vocab_file = config['data'].get(
            'trg_vocab', os.path.join(model_dir, 'trg_vocab.txt')
        )
        src_vocab = Vocabulary(file=src_vocab_file)
        trg_vocab = Vocabulary(file=trg_vocab_file)

        level = config['data']['level']
        lowercase = config['data']['lowercase']

        tok_fun = list if level == 'char' else lambda s: s.split()

        src_field = Field(init_token=None, eos_token=EOS_TOKEN,
                          pad_token=PAD_TOKEN, tokenize=tok_fun,
                          batch_first=True, lower=lowercase,
                          unk_token=UNK_TOKEN, include_lengths=True)
        src_field.vocab = src_vocab

        trg_field = Field(init_token=BOS_TOKEN, eos_token=EOS_TOKEN,
                          pad_token=PAD_TOKEN, tokenize=tok_fun,
                          unk_token=UNK_TOKEN, batch_first=True,
                          lower=lowercase, include_lengths=True)
        trg_field.vocab = trg_vocab

        (batch_size, batch_type, use_cuda, n_gpu, level, eval_metric,
         max_output_length, beam_size, beam_alpha, postprocess,
         bpe_type, sacrebleu, decoding_description,
         tokenizer_info, tag_dict_file) = parse_test_args(config,
                                                          mode='translate')
        test_args = {
            'batch_size': batch_size, 'batch_type': batch_type,
            'use_cuda': use_cuda, 'n_gpu': n_gpu, 'level': level,
            'eval_metric': eval_metric, 'max_output_length': max_output_length,
            'beam_size': beam_size, 'beam_alpha': beam_alpha,
            'postprocess': postprocess, 'bpe_type': bpe_type,
            'sacrebleu': sacrebleu, 'decoding_description': decoding_description,
            'tokenizer_info': tokenizer_info, 'tag_dict_file': tag_dict_file
        }

        model = build_model(config['model'], src_vocab=src_vocab,
                            trg_vocab=trg_vocab)
        ckpt = get_latest_checkpoint(model_dir)
        config['training']['load_model'] = ckpt
        config['training']['reset_best_ckpt'] = False
        config['training']['reset_scheduler'] = True
        config['training']['reset_optimizer'] = True
        train_manager = TrainManager(model=model, config=config)

        #model_checkpoint = load_checkpoint(ckpt, use_cuda=test_args['use_cuda'])
        #model.load_state_dict(model_checkpoint['model_state'])

        return cls(config=config, model=model, train_manager=train_manager,
                   src_field=src_field, trg_field=trg_field,
                   test_args=test_args, joey_dir=joey_dir)

    @property
    def train_dataset(self):
        if not self._train_dataset:
            self._train_dataset = self._load_train_dataset()
        return self._train_dataset

    def is_still_latest(self):
        train_config = self.config['training']
        latest_checkpoint = get_latest_checkpoint(train_config['model_dir'])
        return latest_checkpoint == train_config['load_model']

    def get_batch_size_fn(self):
        if self.config['training'].get('batch_type') == "token":
            return token_batch_size_fn
        return None

    def _load_train_dataset(self, path=None):
        if not path:
            path = self.config['data']['train']
        path = _resolve_path(path, self.joey_dir)

        src_lang = self.config['data']['src']
        trg_lang = self.config['data']['trg']
        max_sent_length = self.config['data']['max_sent_length']
        dataset = TranslationDataset(
            path=path, exts=("." + src_lang, "." + trg_lang),
            fields=(self.src_field, self.trg_field, ID_FIELD),
            filter_pred= lambda x: len(vars(x)['src']) <= max_sent_length
            and len(vars(x)['trg']) <= max_sent_length
        )
        for example in dataset:
            setattr(example, 'id', -1)
        return dataset

    def get_config_dataset(self, name):
        return self._load_train_dataset(self.config['data'][name])

    def validate(self, dataset, **kwargs):
        valid_kwargs = {k: v for k, v in self.test_args.items()
                        if k not in ['decoding_description', 'tokenizer_info',
                                     'tag_dict_file']}
        valid_kwargs['eval_metric'] = ''
        valid_kwargs['compute_loss'] = False
        valid_kwargs['data'] = dataset
        valid_kwargs.update(kwargs)

        (score, loss, ppl, sources, sources_raw, references, hypotheses,
         hypotheses_raw, valid_attention_scores) = validate_on_data(
             self.model, **valid_kwargs)

        return {
            'score': score,
            'loss': loss,
            'ppl': ppl,
            'sources': sources,
            'sources_raw': sources_raw,
            'references': references,
            'hypotheses': hypotheses,
            'hypotheses_raw': hypotheses_raw,
            'valid_attention_scores': valid_attention_scores,
        }

    def translate(self, sentences, **kwargs):
        dataset = make_dataset(sentences, self.src_field)
        results = self.validate(dataset, **kwargs)
        return results['hypotheses']

    def translate_single(self, sentence):
        hypotheses = self.translate([sentence])
        return hypotheses[0]

    def train(self, batches, dev_set=None, batch_callback=None):
        logging.info('Training model {}.'
                     .format(self.config['training']['model_dir']))

        # Shorter name
        trainer = self.train_manager

        if dev_set == 'dev2':
            if 'dev2' in self.config['data']:
                logging.info('Using dev2 as dev set')
                dev_set = self.get_config_dataset('dev2')
            else:
                dev_set = 'dev'
        if dev_set == 'dev':
            logging.info('Using dev as dev set')
            dev_set = self.get_config_dataset('dev')

        if dev_set:
            dev_results = self.validate(dev_set)
            logging.info('Validation result: {}'.format(dev_results['score']))

        for i, batch in enumerate(batches):
            logging.info('Training on batch {}.'.format(i + 1))
            logging.info('IDs in batch: {}'.format(batch.id))
            joey_batch = Batch(batch, self.model.pad_index,
                               use_cuda=trainer.use_cuda)
            trainer._train_step(joey_batch)
            if (i + 1) % trainer.batch_multiplier == 0:
                if trainer.clip_grad_fun:
                    trainer.clip_grad_fun(params=trainer.model.parameters())
                trainer.optimizer.step()
                if trainer.scheduler and trainer.scheduler_step_at == 'step':
                    trainer.scheduler.step()

                trainer.model.zero_grad()
                trainer.stats.steps += 1
            if batch_callback:
                batch_callback(batch)
        logging.info('Finished training after {} batches'.format(i + 1))

        trainer._save_checkpoint()

        if dev_set:
            dev_results = self.validate(dev_set)
            logging.info('Validation result: {}'.format(dev_results['score']))
