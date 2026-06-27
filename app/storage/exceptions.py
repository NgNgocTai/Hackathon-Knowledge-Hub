class StorageError(Exception):
    pass


class VectorStoreError(StorageError):
    pass


class GraphStoreError(StorageError):
    pass
