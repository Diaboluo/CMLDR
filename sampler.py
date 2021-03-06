import numpy as np
from multiprocessing import Process, Queue
from scipy.sparse import lil_matrix


def sample_function(user_item_matrix, batch_size, n_negative, result_queue, check_negative=True):
    """

    :param user_item_matrix: the user-item matrix for positive user-item pairs
    :param batch_size: number of samples to return
    :param n_negative: number of negative samples per user-positive-item pair
    :param result_queue: the output queue
    :return: None
    """
    user_item_matrix = lil_matrix(user_item_matrix)
    user_item_pairs = np.asarray(user_item_matrix.nonzero()).T
    user_to_positive_set = {u: set(row) for u, row in enumerate(user_item_matrix.rows)}
    np.random.seed(10)
    while True:
        np.random.shuffle(user_item_pairs)
        m_num = int(len(user_item_pairs) / batch_size)
        for i in range(m_num):
            user_positive_items_pairs = user_item_pairs[i * batch_size: (i + 1) * batch_size, :]

            # sample negative samples
            negative_samples = np.random.randint(
                0,
                user_item_matrix.shape[1],
                size=(batch_size, n_negative))

            # Check if we sample any positive items as negative samples.
            # Note: this step can be optional as the chance that we sample a positive item is fairly low given a
            # large item set.
            if check_negative:
                for user_positive, negatives, i in zip(user_positive_items_pairs,
                                                       negative_samples,
                                                       range(len(negative_samples))):
                    user = user_positive[0]
                    for j, neg in enumerate(negatives):
                        while neg in user_to_positive_set[user]:
                            negative_samples[i, j] = neg = np.random.randint(0, user_item_matrix.shape[1])
            result_queue.put((user_positive_items_pairs, negative_samples))


class WarpSampler(object):
    """
    A generator that generates tuples: user-positive-item pairs, negative-items

    of the shapes (Batch Size, 2) and (Batch Size, N_Negative)
    """

    def __init__(self, user_item_matrix, batch_size=50, n_negative=10,check_negative=True):
        self.result_queue = Queue(maxsize=10)
        self.processors = []
        self.processors.append(
            Process(target=sample_function, args=(user_item_matrix,
                                                  batch_size,
                                                  n_negative,
                                                  self.result_queue,
                                                  check_negative)))
        self.processors[-1].start()

    def next_batch(self):
        return self.result_queue.get()

    def close(self):
        for p in self.processors:  # type: Process
            p.terminate()
            p.join()


