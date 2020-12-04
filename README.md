# goodenough

A small Python lib that helps one to pick items from their collections / storages.

It's designed for tasks where you need a random item that is also not complete garbage like selecting the next song from a songs database to play on the radio.

To use this lib you should tell it how to get the sample of items (`get_items`) and how to sort them from good to bad (`rules`).

Optionaly, you can also reflect on how the items got sorted and which item has won (`review_items`).

All callbacks should be async in case you want to do I/O stuff (like talking to a storage).

See tests.
