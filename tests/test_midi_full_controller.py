from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
from unittest import mock
import mido
import logging
import json
import jsonpickle
import os
import zlib
from audioled import serverconfiguration, version, project
from audioled_controller import midi_full, sysex_data

# Taken from pyupdater test repo
class TConfig(object):
    bad_attr = "bad attr"
    # If left None "Not_So_TUF" will be used
    APP_NAME = "Molecole Test"

    COMPANY_NAME = "Digital"

    DATA_DIR = None

    # Public Key used by your app to verify update data
    # REQUIRED
    PUBLIC_KEY = "rRp4eJzzsPxN1nLXBOuLCqI33HWTridHKJpNnDSUlbU"

    # Online repository where you host your packages
    # and version file
    # REQUIRED
    UPDATE_URLS = []
    UPDATE_PATCHES = True

    # Upload Setup
    REMOTE_DIR = None
    HOST = None

    # Tests seem to fail when this is True
    VERIFY_SERVER_CERT = True

def test_get_version():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    version._test_version = "1.0.0"
    # Get Version messsage
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x00]
    # Handle message
    ctrl.handleMidiMsg(testMsg, None, None)
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x00
    # Decode data
    dec = sysex_data.decode(retMsg.data[2:])
    v = str(bytes(dec), encoding='utf8')
    # Check is version string
    assert len(v.split('.')) >= 3

def test_update_check_update_not_available(caplog, tmpdir):
    caplog.set_level(logging.DEBUG)
    logging.debug("UPDATE TEST")
    f = mock.Mock()
    version._test_version = "0.0.0"
    tmpDirPath = os.path.join(tmpdir, "pyu-data", "deploy")
    # tmpDirPath = os.getcwd()  # Enable for testing after creating release or release-dev
    # Write test files
    if not os.path.exists(tmpDirPath):
        os.makedirs(tmpDirPath)

    opts = midi_full.MidiProjectControllerOptions()
    opts.update_paths = [os.path.join(tmpDirPath, "pyu-data", "deploy")]
    # opts.client_config = TConfig()
    ctrl = midi_full.MidiProjectController(callback=f, options=opts)
    # Update message
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x11]
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, None)
    if f.call_count > 0:
        retMsg = f.call_args[0][0]
        assert retMsg.data[0] == 0x00
        assert retMsg.data[1] == 0x1F

def test_get_active_project():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x20]
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    proj.stopProcessing()
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x20
    # Decode data
    dec = sysex_data.decode(retMsg.data[2:])
    metadata = json.loads(bytes(dec))
    assert metadata is not None
    assert metadata['name'] == 'Default project'

def test_get_projects():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x30]
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    cfg.initDefaultProject()
    proj.stopProcessing()
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, None)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x30
    # Decode data
    dec = sysex_data.decode(retMsg.data[2:])
    assert dec is not None
    metadata = json.loads(bytes(dec))
    assert metadata is not None
    # TODO: Adjust check
    assert len(metadata.keys()) == 2

def test_activate_project_successful():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()  # type: project.Project
    proj.stopProcessing()
    # Activate project
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x40] + sysex_data.encode(bytes(proj.id, encoding='utf8'))
    
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x40

def test_activate_project_not_found():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x40] + sysex_data.encode(bytes("blubb", encoding='utf8'))
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    proj.stopProcessing()
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x4F

def test_import_project_successful():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    proj.stopProcessing()
    assert len(cfg.getProjectsMetadata().keys()) == 1
    proj.id = "testproj"
    projJson = jsonpickle.encode(proj)
    print(projJson)
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x50] + sysex_data.encode(bytes(projJson, encoding='utf8'))
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x50
    assert len(cfg.getProjectsMetadata().keys()) == 2

def test_import_project_error():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()  # type: project.Project
    proj.stopProcessing()
    # Activate project
    testMsg = mido.Message('sysex')
    invalidJson = jsonpickle.encode(testMsg)
    testMsg.data = [0x00, 0x50] + sysex_data.encode(bytes(invalidJson, encoding='utf8'))
    
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x5F

def test_export_project():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    proj.stopProcessing()
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x60] + sysex_data.encode(proj.id)
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x60
    # Decode data
    dec = sysex_data.decode(retMsg.data[2:])
    dec = zlib.decompress(bytes(dec))
    restoredProj = jsonpickle.loads(dec)  # type project.Project
    assert restoredProj is not None
    assert restoredProj.id == proj.id

def test_export_project_not_found():
    # Setup
    f = mock.Mock()
    ctrl = midi_full.MidiProjectController(callback=f)
    # Get active project metadata
    testMsg = mido.Message('sysex')
    testMsg.data = [0x00, 0x60] + sysex_data.encode(bytes("blubb", encoding='utf8'))
    # Init in-memory config
    cfg = serverconfiguration.ServerConfiguration()
    proj = cfg.getActiveProjectOrDefault()
    proj.stopProcessing()
    # Handle message
    ctrl.handleMidiMsg(testMsg, cfg, proj)
    assert f.call_count == 1
    retMsg = f.call_args[0][0]
    # Check response message ID
    assert retMsg.data[0] == 0x00
    assert retMsg.data[1] == 0x6F