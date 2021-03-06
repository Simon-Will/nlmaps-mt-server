import itertools
import random

from torchtext.data import Batch, BucketIterator, Dataset, Example, Field
from torchtext.data.utils import RandomShuffler


ID_FIELD = Field(sequential=False, use_vocab=False, batch_first=True)


def make_dataset(src, src_field, trg_field=None, trg=None, ids=None):
    fields = [('src', src_field)]
    data = [src]
    if trg and trg_field:
        fields.append(('trg', trg_field))
        data.append(trg)
    if ids:
        fields.append(('id', ID_FIELD))
        data.append(ids)

    examples = [Example.fromlist(sentences, fields) for sentences in zip(*data)]
    dataset = Dataset(examples, fields)
    return dataset


class MyRandomShuffler(RandomShuffler):

    def __call__(self, data):
        return random.sample(data, len(data))


class MyBucketIterator(BucketIterator):

    def __init__(self, *args, max_epochs=None, deterministic=False, **kwargs):
        self.max_epochs = max_epochs
        super().__init__(*args, **kwargs)

        if not deterministic:
            self.random_shuffler = MyRandomShuffler()

    def iter_batches_as_lists(self):
        """Mostly a copy of BucketIterator.__iter__, but yielding the
        batches as lists of sentences instead of Batch objects.
        """
        while True:
            self.init_epoch()
            for idx, minibatch in enumerate(self.batches):
                # fast-forward if loaded from state
                if self._iterations_this_epoch > idx:
                    continue
                self.iterations += 1
                self._iterations_this_epoch += 1
                if self.sort_within_batch:
                    # NOTE: `rnn.pack_padded_sequence` requires that a minibatch
                    # be sorted by decreasing order, which requires reversing
                    # relative to typical sort keys
                    if self.sort:
                        minibatch.reverse()
                    else:
                        minibatch.sort(key=self.sort_key, reverse=True)
                yield minibatch
            if not self.repeat or (
                    self.max_epochs and self.epoch >= self.max_epochs):
                return


def merge_iterators(main_iterator, *rest_iterators, yield_list=False):
    batch_iterators = [iterator.iter_batches_as_lists()
                       for iterator in [main_iterator, *rest_iterators]]
    for batches in zip(*batch_iterators):
        batch = list(itertools.chain.from_iterable(batches))
        if main_iterator.sort_within_batch:
            batch.sort(key=main_iterator.sort_key, reverse=True)
        if yield_list:
            yield batch
        else:
            yield Batch(batch, main_iterator.dataset, main_iterator.device)
