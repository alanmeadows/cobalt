# Copyright 2011 GridCentric Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""Handles all requests relating to GridCentric functionality."""

from nova import compute
from nova import flags
from nova import log as logging
from nova.db import base
from nova import quota
from nova import rpc
from nova.openstack.common import cfg

LOG = logging.getLogger('gridcentric.nova.api')
FLAGS = flags.FLAGS

gridcentric_api_opts = [
               cfg.StrOpt('gridcentric_topic',
               default='gridcentric',
               help='the topic gridcentric nodes listen on') ]
FLAGS.register_opts(gridcentric_api_opts)

class API(base.Base):
    """API for interacting with the gridcentric manager."""

    def __init__(self, **kwargs):
        super(API, self).__init__(**kwargs)
        self.compute_api = compute.API()

    def get(self, context, instance_uuid):
        """Get a single instance with the given instance_uuid."""
        rv = self.db.instance_get_by_uuid(context, instance_uuid)
        return dict(rv.iteritems())

    def _cast_gridcentric_message(self, method, context, instance_uuid, host=None,
                              params=None):
        """Generic handler for RPC casts to gridcentric. This does not block for a response.

        :param params: Optional dictionary of arguments to be passed to the
                       gridcentric worker

        :returns: None
        """

        if not params:
            params = {}
        if not host:
            instance = self.get(context, instance_uuid)
            host = instance['host']
        queue = self.db.queue_get_for(context, FLAGS.gridcentric_topic, host)
        params['instance_uuid'] = instance_uuid
        kwargs = {'method': method, 'args': params}
        rpc.cast(context, queue, kwargs)

    def _call_gridcentric_message(self, method, context, instance_uuid, host=None,
                              params=None):
        """Generic handler for RPC call to gridcentric. This will block for a response.

        :param params: Optional dictionary of arguments to be passed to the
                       gridcentric worker

        :returns: None
        """

        if not params:
            params = {}
        if not host:
            instance = self.get(context, instance_uuid)
            host = instance['host']
        queue = self.db.queue_get_for(context, FLAGS.gridcentric_topic, host)
        params['instance_uuid'] = instance_uuid
        kwargs = {'method': method, 'args': params}
        rpc.call(context, queue, kwargs)

    def _check_quota(self, context, instance_uuid):
        # Check the quota to see if we can launch a new instance.
        instance = self.get(context, instance_uuid)
        instance_type = instance['instance_type']
        metadata = instance['metadata']

        # check the quota to if we can launch a single instance.
        num_instances = quota.allowed_instances(context, 1, instance['instance_type'])
        if num_instances < 1:
            pid = context.project_id
            LOG.warn(_("Quota exceeded for %(pid)s,"
                    " tried to launch an instance"))
            if num_instances <= 0:
                message = _("Instance quota exceeded. You cannot run any "
                            "more instances of this type.")
            else:
                message = _("Instance quota exceeded. You can only run %s "
                            "more instances of this type.") % num_instances
            raise quota.QuotaError(message, "InstanceLimitExceeded")

        # check against metadata
        metadata = self.db.instance_metadata_get(context, instance_uuid)
        self.compute_api._check_metadata_properties_quota(context, metadata)

    def bless_instance(self, context, instance_uuid):
        LOG.debug(_("Casting gridcentric message for bless_instance") % locals())
        self._cast_gridcentric_message('bless_instance', context, instance_uuid)

    def discard_instance(self, context, instance_uuid):
        LOG.debug(_("Casting gridcentric message for discard_instance") % locals())
        self._cast_gridcentric_message('discard_instance', context, instance_uuid)

    def launch_instance(self, context, instance_uuid):
        pid = context.project_id
        uid = context.user_id

        self._check_quota(context, instance_uuid)

        instance = self.get(context, instance_uuid)

        LOG.debug(_("Casting to scheduler for %(pid)s/%(uid)s's"
                    " instance %(instance_uuid)s") % locals())
        rpc.cast(context,
                     FLAGS.scheduler_topic,
                     {"method": "launch_instance",
                      "args": {"topic": FLAGS.gridcentric_topic,
                               "instance_uuid": instance_uuid}})

    def list_launched_instances(self, context, instance_uuid):
        filter = {
                  'metadata':{'launched_from':'%s' % instance_uuid},
                  'deleted':False
                  }
        launched_instances = self.compute_api.get_all(context, filter)
        return launched_instances

    def list_blessed_instances(self, context, instance_uuid):
        filter = {
                  'metadata':{'blessed_from':'%s' % instance_uuid},
                  'deleted':False
                  }
        blessed_instances = self.compute_api.get_all(context, filter)
        return blessed_instances
