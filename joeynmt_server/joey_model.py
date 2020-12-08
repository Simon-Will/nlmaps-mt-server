import pathlib

from torchtext.data import Dataset, Example, Field

from joeynmt.constants import UNK_TOKEN, PAD_TOKEN, EOS_TOKEN
from joeynmt.data import MonoDataset
from joeynmt.helpers import (load_config, get_latest_checkpoint,
                             load_checkpoint)
from joeynmt.model import build_model
from joeynmt.prediction import parse_test_args, validate_on_data
from joeynmt.vocabulary import Vocabulary


class JoeyModel:

    def __init__(self, config, model, src_field, test_args):
        self.config = config
        self.model = model
        self.src_field = src_field
        self.test_args = test_args

    @classmethod
    def from_config_file(cls, config_file, joey_dir):
        config = load_config(config_file)
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
                          unk_token=UNK_TOKEN,
                          include_lengths=True)
        src_field.vocab = src_vocab

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
                   test_args=test_args)

    def make_dataset(self, sentences):
        fields = [('src', self.src_field)]
        examples = [Example.fromlist([sentence], fields)
                    for sentence in sentences]
        return Dataset(examples, fields)

    def translate(self, sentences):
        dataset = self.make_dataset(sentences)

        kwargs = {k: v for k, v in self.test_args.items()
                  if k not in ['decoding_description', 'tokenizer_info']}
        kwargs['eval_metric'] = ''
        kwargs['compute_loss'] = False
        kwargs['data'] = dataset

        _, _, _, _, _, _, hypotheses, _, _ = validate_on_data(self.model,
                                                              **kwargs)
        return hypotheses

    def translate_single(self, sentence):
        hypotheses = self.translate([sentence])
        return hypotheses[0]
