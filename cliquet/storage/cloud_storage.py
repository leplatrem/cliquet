from functools import wraps

import requests
import six
from requests.exceptions import HTTPError

from cliquet import logger
from cliquet.storage import (StorageBase, exceptions, get_unicity_rules,
                             Filter, apply_sorting)
from cliquet.utils import json, COMPARISON


API_PREFIX = "/v0"

DEFAULT_CLOUD_STORAGE_URL = 'https://cloud-storage.services.mozilla.com'

FILTERS = {
    COMPARISON.LT: 'lt_',
    COMPARISON.MIN: 'min_',
    COMPARISON.MAX: 'max_',
    COMPARISON.NOT: 'not_',
    COMPARISON.EQ: '',
    COMPARISON.GT: 'gt_',
}


def wrap_http_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            status_code = e.response.status_code
            body = e.response.json()
            if status_code == 404:
                record_id = '?'
                raise exceptions.RecordNotFoundError(record_id)
            if status_code == 409:
                import re
                m = re.search('Conflict of field (\w)', body['message'])
                field = m.group(0)
                record = body['existing']
                raise exceptions.UnicityError(field, record)
            if status_code == 412:
                raise exceptions.IntegrityError()
            # 304 ?
            logger.debug(body)
            raise exceptions.BackendError()
    return wrapped


class CloudStorage(StorageBase):

    def __init__(self, *args, **kwargs):
        super(CloudStorage, self).__init__()

        self._client = requests.Session()
        self.server_url = kwargs.get('server_url', DEFAULT_CLOUD_STORAGE_URL)

    def _build_url(self, resource):
        return self.server_url + API_PREFIX + resource

    def _build_headers(self, resource):
        original = resource.request
        auth_token = original.headers['Authorization']
        return {
            'Content-Type': 'application/json',
            'Authorization': auth_token
        }

    @wrap_http_error
    def flush(self):
        url = self._build_url("/__flush__")
        resp = self._client.post(url)
        resp.raise_for_status()

    def ping(self):
        url = self._build_url("/__heartbeat__")
        resp = self._client.get(url)
        return resp.status_code == 200

    @wrap_http_error
    def collection_timestamp(self, resource, user_id):
        """Return the last timestamp for the resource collection of the user"""
        url = self._build_url("/collections/%s/records" % resource.name)
        resp = self._client.head(url, headers=self._build_headers(resource))
        resp.raise_for_status()
        return int(resp.headers['Last-Modified'])

    def check_unicity(self, resource, user_id, record):
        rules = get_unicity_rules(resource, user_id, record)
        for rule in rules:
            new_rule = []
            for filter_ in rule:
                value = filter_.value
                if isinstance(value, six.string_types):
                    filter_ = Filter(filter_.field, "'%s'" % filter_.value,
                                     filter_.operator)
                new_rule.append(filter_)

            result, count = self.get_all(resource, user_id, new_rule)
            if count != 0:
                raise exceptions.UnicityError(rule[0].field,
                                              result[0])

    @wrap_http_error
    def create(self, resource, user_id, record):
        self.check_unicity(resource, user_id, record)
        url = self._build_url("/collections/%s/records" % resource.name)
        resp = self._client.post(url,
                                 data=json.dumps(record),
                                 headers=self._build_headers(resource))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def get(self, resource, user_id, record_id):
        url = self._build_url("/collections/%s/records/%s" % (
            resource.name, record_id))
        resp = self._client.get(url, headers=self._build_headers(resource))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def update(self, resource, user_id, record_id, record):
        self.check_unicity(resource, user_id, record)
        url = self._build_url("/collections/%s/records/%s" % (
            resource.name, record_id))
        try:
            self.get(resource, user_id, record_id)
        except exceptions.RecordNotFoundError:
            resp = self._client.put(url,
                                    data=json.dumps(record),
                                    headers=self._build_headers(resource))
        else:
            if resource.id_field in record:
                del record[resource.id_field]
            resp = self._client.patch(url,
                                      data=json.dumps(record),
                                      headers=self._build_headers(resource))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def delete(self, resource, user_id, record_id):
        url = self._build_url("/collections/%s/records/%s" % (
            resource.name, record_id))
        resp = self._client.delete(url, headers=self._build_headers(resource))
        resp.raise_for_status()
        return resp.json()

    def delete_all(self, resource, user_id, filters=None):
        url = self._build_url("/collections/%s/records" % resource.name)
        params = []
        if filters:
            params += [("%s%s" % (FILTERS[op], k), v) for k, v, op in filters]
        resp = self._client.delete(url,
                                   params=params,
                                   headers=self._build_headers(resource))
        resp.raise_for_status()

    @wrap_http_error
    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        url = self._build_url("/collections/%s/records" % resource.name)

        params = []

        sort_fields = []
        if sorting:
            for field, direction in sorting:
                prefix = '-' if direction < 0 else ''
                sort_fields.append(prefix + field)

        if sort_fields:
            params += [("_sort", ','.join(sort_fields))]

        if filters:
            params += [("%s%s" % (FILTERS[op], k), v)
                       for k, v, op in filters]

        if limit:
            params.append(("_limit", limit))

        resp = self._client.get(url,
                                params=params,
                                headers=self._build_headers(resource))
        resp.raise_for_status()
        count = resp.headers.get('Total-Records')

        if pagination_rules:
            records = {}
            for filters in pagination_rules:
                request_params = list(params)
                request_params += [("%s%s" % (FILTERS[op], k), v)
                                   for k, v, op in filters]
                resp = self._client.get(url,
                                        params=request_params,
                                        headers=self._build_headers(resource))
                resp.raise_for_status()
                for record in resp.json()['items']:
                    records[record[resource.id_field]] = record

            if sorting:
                records = apply_sorting(records.values(), sorting)[:limit]
        else:
            records = resp.json()['items']

        return records, int(count)


def load_from_config(config):
    settings = config.registry.settings
    server_url = settings.get('cliquet.storage_url')
    return CloudStorage(server_url=server_url)