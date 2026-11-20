# Search evaluation

24 labelled queries, top 10 results.

| Method | Recall@10 | MRR | nDCG@10 | Median latency (ms) |
| --- | --- | --- | --- | --- |
| keyword | 0.492 | 0.835 | 0.783 | 61 |
| vector | 0.500 | 0.876 | 0.796 | 123 |
| hybrid | 0.495 | 0.857 | 0.802 | 128 |
| rerank | 0.487 | 0.824 | 0.785 | 3095 |

## nDCG@10 by query type

| Method | en | filter | skill | sv |
| --- | --- | --- | --- | --- |
| keyword | 0.889 | 0.685 | 0.538 | 0.894 |
| vector | 0.853 | 0.738 | 0.523 | 1.000 |
| hybrid | 0.873 | 0.769 | 0.487 | 1.000 |
| rerank | 0.819 | 0.791 | 0.526 | 0.972 |
