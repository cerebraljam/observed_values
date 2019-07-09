# Breached Credentials Oracle

This service is using a [Bloom Filter](https://en.wikipedia.org/wiki/Bloom_filter) to record the fact that a credential is known to have been breached.

Then by doing the same calculation on a given credential, we can check if it has been observed already.

The bloom filter does not contain any information. Therefore, we don't need to worry about keeping that database protected against leakage.

The code is a server version of this Jupyter Notebook: https://github.com/cerebraljam/observed_values
