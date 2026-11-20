# Search evaluation

28 labelled queries, top 10 results.

| Method | Recall@10 | MRR | nDCG@10 | Median latency (ms) |
| --- | --- | --- | --- | --- |
| keyword | 0.505 | 0.695 | 0.557 | 58 |
| vector | 0.464 | 0.694 | 0.517 | 118 |
| hybrid | 0.435 | 0.652 | 0.506 | 121 |
| rerank | 0.498 | 0.592 | 0.538 | 2975 |

## nDCG@10 by query type

| Method | en | filter | skill | sv |
| --- | --- | --- | --- | --- |
| keyword | 0.561 | 0.685 | 0.400 | 0.602 |
| vector | 0.549 | 0.738 | 0.396 | 0.371 |
| hybrid | 0.522 | 0.769 | 0.345 | 0.410 |
| rerank | 0.537 | 0.791 | 0.474 | 0.399 |
