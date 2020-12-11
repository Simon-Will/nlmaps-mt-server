import pathlib

from torchtext.data import Dataset, Example, Field, TranslationDataset

from joeynmt.constants import BOS_TOKEN, EOS_TOKEN, PAD_TOKEN, UNK_TOKEN
from joeynmt.data import MonoDataset, token_batch_size_fn
from joeynmt.helpers import (load_config, get_latest_checkpoint,
                             load_checkpoint)
from joeynmt.model import build_model
from joeynmt.prediction import parse_test_args, validate_on_data
from joeynmt.training import TrainManager
from joeynmt.vocabulary import Vocabulary

from joeynmt_server.utils.batching import make_dataset

class JoeyModel:

    def __init__(self, config, model, src_field, trg_field, test_args):
        self.config = config
        self.model = model
        self.src_field = src_field
        self.trg_field = trg_field
        self.test_args = test_args

    @classmethod
    def from_config_file(cls, config_file, joey_dir, use_cuda=None):
        config = load_config(config_file)
        if use_cuda is not None:
            config['training']['use_cuda'] = use_cuda

        model_dir = pathlib.Path(config['training']['model_dir'])
        if not model_dir.is_absolute():
            model_dir = pathlib.Path(joey_dir) / model_dir


        src_vocab_file = config['data'].get('src_vocab',
                                            model_dir / 'src_vocab.txt')
        trg_vocab_file = config['data'].get('trg_vocab',
                                            model_dir / 'trg_vocab.txt')
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
         tokenizer_info) = parse_test_args(config, mode='translate')
        test_args = {
            'batch_size': batch_size, 'batch_type': batch_type,
            'use_cuda': use_cuda, 'n_gpu': n_gpu, 'level': level,
            'eval_metric': eval_metric, 'max_output_length': max_output_length,
            'beam_size': beam_size, 'beam_alpha': beam_alpha,
            'postprocess': postprocess, 'bpe_type': bpe_type,
            'sacrebleu': sacrebleu, 'decoding_description': decoding_description,
            'tokenizer_info': tokenizer_info,
        }

        ckpt = get_latest_checkpoint(model_dir)
        model_checkpoint = load_checkpoint(ckpt,
                                           use_cuda=test_args['use_cuda'])
        model = build_model(config['model'], src_vocab=src_vocab,
                            trg_vocab=trg_vocab)
        model.load_state_dict(model_checkpoint['model_state'])

        if test_args['use_cuda']:
            model.cuda()

        return cls(config=config, model=model, src_field=src_field,
                   trg_field=trg_field, test_args=test_args)

    @property
    def train_dataset(self):
        if not self.train_dataset:
            self.train_dataset = self._load_train_dataset()
        return self.train_dataset

    def get_batch_size_fn(self):
        if self.config['train'].get('batch_type') == "token":
            return token_batch_size_fn
        return None

    def _load_train_dataset(self, path=None):
        if not path:
            path = self.config.data['train']

        src_lang = self.config.data['src']
        trg_lang = self.config.data['trg']
        max_sent_length = self.config.data['max_sent_length']
        dataset = TranslationDataset(
            path=path, exts=("." + src_lang, "." + trg_lang),
            fields=(self.src_field, self.trg_field),
            filter_pred= lambda x: len(vars(x)['src']) <= max_sent_length
            and len(vars(x)['trg']) <= max_sent_length
        )
        return dataset

    def _validate_on_data(self, dataset, **kwargs):
        valid_kwargs = {k: v for k, v in self.test_args.items()
                        if k not in ['decoding_description', 'tokenizer_info']}
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
        results = self._validate_on_data(dataset, **kwargs)
        return results['hypotheses']

    def translate_single(self, sentence):
        hypotheses = self.translate([sentence])
        return hypotheses[0]

    def train(self, batches, dev_set=None):
        trainer = TrainManager(model=self.model, config=self.config)

        if dev_set:
            dev_results = self._validate_on_data(dev_set)

        for i, batch in enumerate(batches):
            print('Training on batch: {}'.format(batch))
            trainer._train_step(batch)
            if (i + 1) % trainer.batch_multiplier == 0:
                if trainer.clip_grad_fun:
                    trainer.clip_grad_fun(params=trainer.model.parameters())
                trainer.optimizer.step()
                if trainer.scheduler:
                    trainer.scheduler.step()

                trainer.model.zero_grad()
                trainer.stats.steps += 1

            if dev_set:
                dev_results = self._validate_on_data(dev_set)
