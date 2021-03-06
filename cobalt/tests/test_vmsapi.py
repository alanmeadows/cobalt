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



import unittest
import cobalt.nova.extension.vmsapi as vms_api


class CapturedVmsCtl(object):
    """
    Instead of actually running the vmsctl command this will just capture
    the command line.
    """
    def __init__(self, vmsctl):
        self.vmsctl = vmsctl
        self.captured_command = None

    def run_command(self, cmd_list):

        self.captured_command = self.vmsctl.vmsctl_command + cmd_list

        action = cmd_list[0]
        stdout = []
        if action == 'bless':
            # Return an appropriate response.
            stdout.append('newname = captured-vms-ctl-name')
            stdout.append('network = None')
            # NOTE(dscannell): Currently vmsctl does not return a correctly
            #                  formatted json for the artifacts output (i.e.
            #                  it uses single quotes instead of double).
            stdout.append("artifacts = {'files': []}")
        return stdout


class CobaltVmsApiTestCase(unittest.TestCase):

    def setUp(self):
        # TODO(dscannell): We will eventually want to parameterized this test
        #                  to deal with all of the supported vms versions.
        self.vmsapi = vms_api.get_vmsapi(version='2.6')
        # Capture the vmsctl output instead of actually running the command.
        self.capture = CapturedVmsCtl(vms_api.Vmsctl(vms_platform='dummy'))
        self.vmsapi.configure(self.capture)

    def test_bless_nomem_nomigration(self):
        bless_result =  self.vmsapi.bless("testbless", "new-testbless")

        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'bless', 'testbless', 'new-testbless'],
                          self.capture.captured_command)
        self.assertEquals('captured-vms-ctl-name', bless_result.newname)
        self.assertEquals(None, bless_result.network)
        self.assertEquals([], bless_result.blessed_files)

    def test_bless_mem_nomigration(self):
        bless_result =  self.vmsapi.bless("testbless", "new-testbless",
                                          mem_url="mem://url")

        # NOTE(dscannell): The empty strings are needed because they
        #                  represent the "empty" options for path and disk_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'bless', 'testbless', 'new-testbless', '', '',
                                    'mem://url'],
            self.capture.captured_command)

    def test_bless_nomem_migration(self):
        bless_result =  self.vmsapi.bless("testbless", "new-testbless",
                                          migration=True)

        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for path, disk_url
        #                  and mem_url.
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'bless', 'testbless', 'new-testbless', '', '', '',
                                    'True'],
            self.capture.captured_command)

    def test_bless_mem_migration(self):
        bless_result =  self.vmsapi.bless("testbless", "new-testbless",
                                          mem_url="mem://url", migration=True)

        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for path and disk_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'bless', 'testbless', 'new-testbless', '', '',
                                    'mem://url', 'True'],
            self.capture.captured_command)

    def test_launch_nomem_nomigration_noguest_nooptions(self):

        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path")

        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'launch', 'testlaunch', 'new-testlaunch', 'path'],
                self.capture.captured_command)

    def test_launch_mem_nomigration_noguest_nooptions(self):
        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path",
                           mem_url="mem://url")

        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for disk_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'launch', 'testlaunch', 'new-testlaunch', 'path',
                                     '', 'mem://url'],
            self.capture.captured_command)


    def test_launch_nomem_migration_noguest_nooptions(self):
        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path",
                           migration=True)

        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for disk_url and
        #                  mem_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'launch', 'testlaunch', 'new-testlaunch', 'path',
                                      '',  '', 'True'],
            self.capture.captured_command)

    def test_launch_nomem_nomigration_guest_nooptions(self):
        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path",
            guest_params={'param1':'value1'})

        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           '-v', 'param1=value1',
                           'launch', 'testlaunch', 'new-testlaunch', 'path'],
            self.capture.captured_command)

    def test_launch_nomem_nomigration_noguest_options(self):
        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path",
            vms_options={'option1':'value1'})

        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           '-o', 'option1=value1',
                           'launch', 'testlaunch', 'new-testlaunch', 'path'],
            self.capture.captured_command)

    def test_launch_mem_migration_guest_options(self):
        self.vmsapi.launch('testlaunch', 'new-testlaunch', 1, "path",
            mem_url='mem://url', migration=True,
            guest_params={'param1':'value1'}, vms_options={'option1':'value1'})

        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for disk_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           '-v', 'param1=value1',
                           '-o', 'option1=value1',
                           'launch', 'testlaunch', 'new-testlaunch', 'path',
                                     '', 'mem://url', 'True'],
            self.capture.captured_command)

    def test_discard_nomem(self):

        self.vmsapi.discard('testdiscard')
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'discard', 'testdiscard'],
            self.capture.captured_command)

    def test_discard_mem(self):
        self.vmsapi.discard('testdiscard', mem_url='mem://url')
        # NOTE(dscannell): The spaces at the end are needed because they
        #                  represent the "empty" options for path and disk_url
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'discard', 'testdiscard', '', '', 'mem://url'],
            self.capture.captured_command)

    def test_pause(self):
        self.vmsapi.pause('testpause')
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'pause', 'testpause'],
            self.capture.captured_command)

    def test_unpause(self):
        self.vmsapi.unpause('testunpause')
        self.assertEquals(['vmsctl',
                           '--use.names',
                           '-p', 'dummy',
                           'unpause', 'testunpause'],
            self.capture.captured_command)