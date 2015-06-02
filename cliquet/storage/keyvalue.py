from cliquet.storage.exceptions import RecordNotFoundError


class KeyValue(object):

    id_field = '_key'
    parent_id = ''
    collection_id = '__keyvalue'

    def __init__(self, storage):
        self._storage = storage

    def ping(self):
        return self._storage.ping()

    def flush(self, parent_id=None, auth=None):
        parent_id = parent_id or self.parent_id
        return self._storage.delete_all(collection_id=self.collection_id,
                                        parent_id=parent_id,
                                        auth=auth)

    def get(self, key, parent_id=None, auth=None):
        parent_id = parent_id or self.parent_id
        return self._storage.get(collection_id=self.collection_id,
                                 parent_id=parent_id,
                                 object_id=key,
                                 id_field=self.id_field,
                                 auth=auth)

    def find(self, filters, parent_id=None, auth=None):
        parent_id = parent_id or self.parent_id
        records, total = self._resource.get_all(
            collection_id=self.collection_id,
            parent_id=parent_id,
            filters=filters,
            id_field=self.id_field,
            auth=auth)
        return records

    def set(self, key, value, parent_id=None, auth=None):
        parent_id = parent_id or self.parent_id
        assert isinstance(value, (dict,))
        try:
            old = self.get(key, parent_id=parent_id, auth=auth)
            record_id = old[self.id_field]
            return self._storage.update(collection_id=self.collection_id,
                                        parent_id=parent_id,
                                        object_id=record_id,
                                        object=value,
                                        id_field=self.id_field,
                                        auth=auth)
        except RecordNotFoundError:
            return self._storage.create(collection_id=self.collection_id,
                                        parent_id=parent_id,
                                        object=value,
                                        id_generator=lambda: key,
                                        id_field=self.id_field,
                                        auth=auth)

    def delete(self, key, parent_id=None, auth=None):
        parent_id = parent_id or self.parent_id
        return self._storage.delete(collection_id=self.collection_id,
                                    parent_id=parent_id,
                                    object_id=key,
                                    id_field=self.id_field,
                                    auth=auth)


def load_from_config(config):
    storage = config.registry.storage
    return KeyValue(storage)
