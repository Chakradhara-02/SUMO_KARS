"""Seeded IoT packet delay and loss; keeps the last received snapshot."""
import copy
import random
import heapq

class Channel:
    def __init__(self, delay=0., loss=0., seed=1, jitter=0., outage=(0.,0.)):
        if delay < 0 or jitter < 0 or not 0 <= loss <= 1:
            raise ValueError('Delay must be >=0; loss must be in [0,1].')
        self.delay, self.loss, self.random = delay, loss, random.Random(seed)
        self.jitter, self.outage = jitter, outage
        self.queue, self.latest = [], None
        self.sent = self.dropped = 0
        self.received = self.out_of_order = 0

    def transmit(self, now, packet):
        self.sent += 1
        if self.outage[0] <= now < self.outage[1] or self.random.random() < self.loss:
            self.dropped += 1
        else:
            delay = max(0., self.delay + (self.random.uniform(-self.jitter, self.jitter) if self.jitter else 0.))
            heapq.heappush(self.queue, (now+delay, self.sent, copy.deepcopy(packet)))
        while self.queue and self.queue[0][0] <= now + 1e-8:
            _, _, delivered = heapq.heappop(self.queue)
            self.received += 1
            if self.latest is None or delivered['time'] >= self.latest['time']:
                self.latest = delivered
            else:
                self.out_of_order += 1
        return self.latest
