import argparse
from collections import namedtuple
from itertools import zip_longest
import logging
import os
import sys
import time
import urllib

import requests

Instance = namedtuple('Instance', ('nl', 'lin'))

NLMAPS_MT_BASE_URL = 'http://localhost:5050'

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    level=logging.INFO
)


def find_and_read_file(dataset_dir, basenames, split, suffix):
    end = '{}.{}'.format(split, suffix)
    suitable_basenames = [name for name in basenames if name.endswith(end)]
    if len(suitable_basenames) == 0:
        logging.warning('Found no file matching *{}'.format(end))
        return []
    if len(suitable_basenames) > 1:
        logging.error('Found more than one file matching *{}'.format(end))
        sys.exit(1)

    path = os.path.join(dataset_dir, suitable_basenames[0])
    with open(path) as f:
        return [line.strip() for line in f]


def load_data(dataset_dir):
    basenames = os.listdir(dataset_dir)
    data = {'train': [], 'dev': [], 'test': []}
    for split in data:
        en = find_and_read_file(dataset_dir, basenames, split, 'en')
        lin = find_and_read_file(dataset_dir, basenames, split, 'lin')

        if len(en) != len(lin):
            if not en:
                logging.error('Could not load {} dataset. {} file missing'
                              .format(split, 'en'))
            if not lin:
                logging.error('Could not load {} dataset. {} file missing'
                              .format(split, 'lin'))
            logging.error('Lengths of en and lin do not match ({} vs. {})'
                          .format(en, lin))
            sys.exit(2)

        data[split] = [Instance(en_, lin_) for en_, lin_ in zip(en, lin)]
    return data


class NLMapsMT:

    def __init__(self, base_url, model, user_id=None):
        parsed = urllib.parse.urlparse(base_url)
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc

        self.model = model
        self.user_id = user_id

    def _make_url(self, path):
        parsed = urllib.parse.ParseResult(
            scheme=self.scheme, netloc=self.netloc, path=path,
            params=None, query=None, fragment=None
        )
        return parsed.geturl()

    def save_feedback(self, instance: Instance, split):
        url = self._make_url('/save_feedback')
        payload = {'model': self.model, 'nl': instance.nl,
                   'correct_lin': instance.lin, 'split': split,
                   'system_lin': ''}
        if self.user_id:
            payload['user_id'] = self.user_id

        logging.info('POST {} to {}'.format(payload, url))
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logging.error('Response status code: {}'.format(resp.status_code))

    def is_training(self):
        url = self._make_url('/train_status')
        logging.debug('GET to {}'.format(url))
        resp = requests.get(url)
        if resp.status_code != 200:
            logging.error('Response status code: {}'.format(resp.status_code))
            return True
        data = resp.json()
        return bool(data.get('still_training'))

    def validate(self, dataset=None):
        url = self._make_url('/validate')
        payload = {'model': self.model}
        if dataset:
            payload['dataset'] = dataset
        logging.info('POST {} to {}'.format(payload, url))
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            logging.error('Response status code: {}'.format(resp.status_code))


def main(dataset_dir, model, wait_time=3, validation_freq=10, dev2=False,
         test_as_dev=False, base_url=NLMAPS_MT_BASE_URL, user_id=None):
    data = load_data(dataset_dir)
    nlmaps_mt = NLMapsMT(base_url, model=model, user_id=user_id)

    for train_idx, (train, dev, test) in enumerate(
            zip_longest(data['train'], data['dev'], data['test']), start=1):
        if train:
            nlmaps_mt.save_feedback(train, 'train')
            time.sleep(wait_time)
        if dev:
            nlmaps_mt.save_feedback(dev, 'dev')
        if test:
            split = 'dev' if test_as_dev else 'test'
            nlmaps_mt.save_feedback(test, split)

        if validation_freq and train_idx % validation_freq == 0:
            while nlmaps_mt.is_training():
                time.sleep(1)
            nlmaps_mt.validate('dev')
            while nlmaps_mt.is_training():
                time.sleep(1)
            if dev2:
                nlmaps_mt.validate('dev2')
                while nlmaps_mt.is_training():
                    time.sleep(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Simulate online training')
    parser.add_argument('dataset_dir', help='Dataset directory. Must contain'
                        ' six files matching in *{train,dev,test}.{en,lin}')
    parser.add_argument('model', help='Path to model config yaml file')
    parser.add_argument('--wait-time', type=int, default=3,
                        help='Number of seconds to wait between saving pieces'
                        ' of feedback.')
    parser.add_argument('--validation-freq', type=int, default=10,
                        help='Validate on dev from model config after every N'
                        ' pieces of feedback.')
    parser.add_argument('--dev2', default=False, action='store_true',
                        help='At validation time, additionally use dev2'
                        ' from model config to validate on.')
    parser.add_argument('--test-as-dev', default=False, action='store_true')
    parser.add_argument('--base-url', default=NLMAPS_MT_BASE_URL,
                        help='Base_Url of the NLMaps MT server.')
    parser.add_argument('--user-id', type=int,
                        help='User ID to use with the NLMaps MT server.')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
