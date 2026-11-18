# Search evaluation

50 labelled queries, top 10 results.

| Method | Recall@10 | MRR | nDCG@10 | Median latency (ms) |
| --- | --- | --- | --- | --- |
| keyword | 0.542 | 1.000 | 0.974 | 87 |
| vector | 0.568 | 1.000 | 1.000 | 233 |
| hybrid | 0.568 | 1.000 | 1.000 | 275 |

## nDCG@10 by query type

| Method | en | filter | skill | sv |
| --- | --- | --- | --- | --- |
| keyword | 1.000 | 1.000 | 0.942 | 0.956 |
| vector | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | 1.000 | 1.000 | 1.000 | 1.000 |
