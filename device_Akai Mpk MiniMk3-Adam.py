# name=AkaiMpkMiniMk3-Adam
# supportedDevices=MPK mini 3
import arrangement
import channels
import device
import general
import launchMapPages
import math
import midi as m
import mixer
import patterns
import playlist
import plugins
import screen
import time
import transport
import ui
import utils

'''
we have 8 different programs available
each program has 2 banks of 8 pads
 - these can send music notes(?), CC signals or PC signals
 - 2x8 pichtes
 - 2x8 CC
 - 2x8 PC
we have 8 knobs
 - these can send CC only?

design:
put each program on a different midi channel, so one script can react to all programs by filtering for the channel

TODOs:
 find a layout you like
 
 think of a code structure that isn't too verbose to do what you want to do (abstract classes? :/)


 '''

# event.midiChan tells us the midi channel -> which of the 8 programs is running -> we could do a range check here
# event.midiId tells us if it's CC, PC (or regular pitch?)
# event.data

# mappings from (signalType[CC,PC], number) to a function (eventData) -> Unit
# we could also do nested dictionarys, for programs, midiId (CC/PC/else?), midiChannel ?
# we could ALSO do SEPERATE CC/PC-dictionarys, and let these be handled by OnControlChange and OnProgramChange listeners respectively
mapping = {
    (m.MIDI_CONTROLCHANGE, ): {"function": lambda e: transport.globalTransport(m.FPT_Undo, 20)} # why is a value needed as the second param and what does it do
}

# this is a nice idea: give names to the magic number signals coming from the device

# KNOBS: depending on program, K1:K8 = 70:77 or 78:86
# absolute and relative also do change
CCKnob_K1 = 78  # Browser navigation
CCKnob_K2 = 80  # Mixer navigation
CCKnob_K3 = 83  # Navigation /Up&Down
CCKnob_K4 = 82  # Window Tabulator
CCKnob_K5 = 81  # Channel Navigation
CCKnob_K6 = 84  # Navigation /Left&Right
CCKnob_K7 = 85  # Previous Preset
CCKnob_K8 = 86  # Tempo +1 -1

# PADS CC
# usually 16:23 BankA and 24:31 on BankB, but also a non-linear 30:45
CCPad_Bank_1_8 = 41  # Enter
CCPad_Bank_1_4 = 45  # Menu
CCPad_Bank_1_6 = 39  # Loop
CCPad_Bank_1_5 = 38  # Play
CCPad_Bank_1_1 = 42  # Stop
CCPad_Bank_1_2 = 43  # Rec
CCPad_Bank_1_7 = 40  # Metronome
CCPad_Bank_1_3 = 35  # WaitForInput
CCPad_Bank_2_8 = 30  # CountDown
CCPad_Bank_2_5 = 34  # Overdub
CCPad_Bank_2_6 = 31  # LoopRecord
CCPad_Bank_2_7 = 44  # Escape---------
CCPad_Bank_2_4 = 32  # Mixer
CCPad_Bank_2_3 = 36  # ChannelRack
CCPad_Bank_2_2 = 33  # PianoRoll
CCPad_Bank_2_1 = 37  # Playlist

# PADS PC: always stays the same, 0:7 on BankA and 8:15 on BankB

Joy1 = 20  # JoyX Navigation up
Joy2 = 21  # JoyY Navigation down


channelRef = channels.channelNumber()
attributes = [
    {'name': 'Redo', 'value': 12, 'function': lambda: transport.globalTransport(m.FPT_Undo, 20)},
    {'name': 'Undo', 'value': 8, 'function': lambda: transport.globalTransport(m.FPT_UndoUp, 21)},
    {'name': 'Cut', 'value': 15, 'function': lambda: transport.globalTransport(m.FPT_Cut, 50)},
    {'name': 'Paste', 'value': 11, 'function': lambda: transport.globalTransport(m.FPT_Paste, 52)},
    {'name': 'Delete', 'value': 14, 'function': lambda: transport.globalTransport(m.FPT_Delete, 54)},
    {'name': 'Insert', 'value': 13, 'function': lambda: transport.globalTransport(m.FPT_Insert, 53)},
    {'name': 'Copy', 'value': 10, 'function': lambda: transport.globalTransport(m.FPT_Copy, 51)},
    {'name': 'Menu1', 'value': 5, 'function': lambda: transport.globalTransport(m.FPT_Menu, 90)},
    {'name': 'ShowWindow', 'value': 4,
     'function': lambda: channels.showCSForm(channels.channelNumber(), 1) if ui.getFocused(
         1) == 1 else transport.globalTransport(m.FPT_NextMixerWindow, 1)},
    {'name': 'browserRight', 'value': 3, 'function': lambda: ui.navigateBrowserTabs(m.FPT_Right)},
    {'name': 'Enter', 'value': 0, 'function': lambda: transport.globalTransport(m.FPT_Enter, 80)},
    {'name': 'Menu', 'value': 1, 'function': lambda: transport.globalTransport(m.FPT_ItemMenu, 91)},
    {'name': 'browserLeft', 'value': 2, 'function': lambda: ui.navigateBrowserTabs(m.FPT_Left)},
    {'name': 'PluginPicker', 'value': 6, 'function': lambda: transport.globalTransport(m.FPT_F8, 1)},
    {'name': 'Escape', 'value': 7, 'function': lambda: transport.globalTransport(m.FPT_Escape, 81)},
    {'name': 'SelectAllCH', 'value': 9, 'function': lambda: (channels.selectAll())}
]


def OnInit():
    print('Akai MPK Mini mk3 script by BananaParadigm, inspired by TayseteDj')
    print('Your Device port number is: ', device.getPortNumber())
    print('MIDI Device name: ', device.getName())

# is this a state container?
class Attributes:
    slot = 0
    CurrentSlot = 0

att = Attributes()

slotSEL_calc = Attributes.CurrentSlot


# class EventData:
#     handled: bool  # (r/w)	set to True to stop event propagtion
#     timestamp: time  # (r)	timestamp of event
#     status: int  # (r/w)	MIDI status
#     data1: int  # (r/w)	MIDI data1
#     data2: int  # (r/w)	MIDI data2
#     port: int  # (r)	MIDI port
#     note: int  # (r/w)	MIDI note number
#     velocity: int  # (r/w)	MIDI velocity
#     pressure: int  # (r/w)	MIDI pressure
#     progNum: int  # (r)	MIDI program number
#     controlNum: int  # (r)	MIDI control number
#     controlVal: int  # (r)	MIDI control value
#     pitchBend: int  # (r)	MIDI pitch bend value
#     sysex: bytes  # (r/w)	MIDI sysex data
#     isIncrement: bool  # (r/w)	MIDI is increament state
#     res: float  # (r/w)	MIDI res
#     inEv: int  # (r/w)	Original MIDI event value
#     outEv: int  # (r/w)	MIDI event output value
#     midiId: int  # (r/w)	MIDI midiID
#     midiChan: int  # (r/w)	MIDI midiChan (0 based)
#     midiChanEx: int  # (r/w)	MIDI midiChanEx
#     pmeflags: int  # (r)	MIDI pmeflags


def OnMidiMsg(event: EventData):
    event.handled = False
    print('MidiId: ', event.midiId, 'EventData1: ', event.data1, 'eventData2: ', event.data2, 'eventMidiChan',
          event.midiChan, 'eventMidiPort: ', event.port)
    if event.midiId == m.MIDI_PROGRAMCHANGE and (event.midiChan == 10 or event.midiChan == 13):  # FL KNTROL PC
        event.handled = True

        for attribute in attributes:
            if event.data1 == attribute['value']:
                attribute['function']()  # Call the corresponding function
                print(attribute['name'])

    if event.midiId == m.MIDI_CONTROLCHANGE and event.midiChan == 10:  ##FL KNTROL CC
        event.handled = True
        if event.data2 > 0:
            if event.data1 == CCKnob_K5:
                if (event.data2 >= 1) & (event.data2 <= 63):
                    print('next on browser')
                    ui.showWindow(m.widBrowser)
                    ui.next()
                    event.handled = True
                    time.sleep(0.01)
                elif (event.data2 >= 64) & (event.data2 <= 127):
                    print('previous on browser')
                    ui.showWindow(m.widBrowser)
                    ui.previous()
                    event.handled = True
                    time.sleep(0.01)

            elif event.data1 == CCKnob_K2:
                if 1 <= event.data2 <= 63:
                    print('Next on mixer')
                    ui.showWindow(m.widMixer)
                    ui.next()
                elif 64 <= event.data2 <= 127:
                    print('Previous on mixer')
                    ui.showWindow(m.widMixer)
                    ui.previous()
                event.handled = True
                time.sleep(0.01)

            elif event.data1 == CCKnob_K3:
                if event.data2 <= 63:
                    channels.setChannelVolume(channels.channelNumber(),
                                              channels.getChannelVolume(channels.channelNumber()) + 0.015)
                    print('Increase volume')
                elif event.data2 >= 64:
                    channels.setChannelVolume(channels.channelNumber(),
                                              channels.getChannelVolume(channels.channelNumber()) - 0.015)
                    print('Decrease volume')

            elif event.data1 == CCKnob_K6:
                if event.data2 <= 5:
                    event.handled = True
                    print('Increase track volume')
                    mixer.setTrackVolume(mixer.trackNumber(), mixer.getTrackVolume(mixer.trackNumber()) + 0.010)
                elif event.data2 >= 111:
                    event.handled = True
                    print('Decrease track volume')
                    mixer.setTrackVolume(mixer.trackNumber(), mixer.getTrackVolume(mixer.trackNumber()) - 0.010)

            elif event.data1 == Joy2:
                if event.data2 <= 7:
                    print('Scroll down')
                    transport.globalTransport(m.FPT_Down, 1)
                elif event.data2 >= 120:
                    print('Scroll up')
                    transport.globalTransport(m.FPT_Up, 1)
                event.handled = True
                time.sleep(0.01)

            elif event.data1 == CCKnob_K1:
                if 1 <= event.data2 <= 63:
                    print('Channel Down')
                    ui.showWindow(m.widChannelRack)
                    transport.globalTransport(m.FPT_Down, 1)
                elif 64 <= event.data2 <= 127:
                    print('Channel Up')
                    ui.showWindow(m.widChannelRack)
                    transport.globalTransport(m.FPT_Up, 1)
                event.handled = True
                time.sleep(0.01)

            elif event.data1 == CCKnob_K4:
                if 1 <= event.data2 <= 63:
                    print('Next window')
                    ui.nextWindow()
                elif 64 <= event.data2 <= 127:
                    print('Previous window')
                    ui.nextWindow()
                event.handled = True

            elif event.data1 == Joy1:
                if event.data2 <= 7:
                    print('Left')
                    transport.globalTransport(m.FPT_Left, 42)
                elif event.data2 >= 120:
                    print('Right')
                    transport.globalTransport(m.FPT_Right, 43)
                event.handled = True

            elif event.data1 == CCKnob_K7:
                if 1 <= event.data2 <= 63:
                    print('Next preset')
                    ui.next()
                elif 64 <= event.data2 <= 127:
                    print('Previous preset')
                    ui.previous()
                event.handled = True

            elif event.data1 == CCKnob_K8:
                if 1 <= event.data2 <= 63:
                    print('Tempo UP')
                    transport.globalTransport(m.FPT_TempoJog, 10)
                elif 64 <= event.data2 <= 127:
                    print('Tempo DOWN')
                    transport.globalTransport(m.FPT_TempoJog, -10)
                event.handled = True

            elif event.data1 == CCPad_Bank_1_6:
                print('Pat/Song')
                transport.setLoopMode()
                event.handled = True

            elif event.data1 == CCPad_Bank_1_5:
                print('Play')
                transport.start()
                event.handled = True

            elif event.data1 == CCPad_Bank_1_8:
                print('Enter')
                transport.globalTransport(m.FPT_Enter, 80)
                event.handled = True

            elif event.data1 == CCPad_Bank_1_4:
                print('Menu')
                transport.globalTransport(m.FPT_ItemMenu, 91)
                event.handled = True

            elif event.data1 == CCPad_Bank_1_1:
                print('Stop')
                transport.stop()
                event.handled = True

            elif event.data1 == CCPad_Bank_1_2:
                print('Record')
                transport.record()
                event.handled = True

            elif event.data1 == CCPad_Bank_1_7:
                print('Escape')
                transport.globalTransport(m.FPT_Escape, 81)
                event.handled = True

            elif event.data1 == CCPad_Bank_1_3:
                print('WaitForInput')
                transport.globalTransport(m.FPT_WaitForInput, 111)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_8:
                print('CountDown')
                transport.globalTransport(m.FPT_CountDown, 115)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_5:
                print('Overdub')
                transport.globalTransport(m.FPT_Overdub, 112)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_6:
                print('LoopRecord')
                transport.globalTransport(m.FPT_LoopRecord, 113)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_7:
                print('Menu2')
                transport.globalTransport(m.FPT_Menu, 90)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_4:
                channelIs = channels.channelNumber()
                print('Mute channel:', channelIs)
                channels.muteChannel(channelIs)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_3:
                print('Metronome')
                transport.globalTransport(m.FPT_Metronome, 110)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_2:
                print('PianoRoll')
                ui.showWindow(m.widPianoRoll)
                event.handled = True

            elif event.data1 == CCPad_Bank_2_1:
                print('Show playlist')
                ui.showWindow(m.widPlaylist)
                event.handled = True
    if event.midiId == m.MIDI_CONTROLCHANGE and event.midiChan == 11:  # FL MIXER
        event.handled = True

        if event.data2 > -0:
            ui.showWindow(m.widMixer)

            track_mapping = {
                20: 1,
                21: 2,
                22: 3,
                23: 4,
                16: 5,
                17: 6,
                18: 7,
                19: 8
            }

            if event.data1 in track_mapping:
                track_number = track_mapping[event.data1]
                print('Mute Track: ', track_number)
                mixer.muteTrack(track_number)

            elif event.data1 in range(70, 78):
                track_number = event.data1 - 69
                print('Mixer ', track_number)
                mixer.setTrackVolume(track_number, event.data2 / 127)

            event.handled = True
    if event.midiId == m.MIDI_CONTROLCHANGE and event.midiChan == 12:  # FL CREATIVE CC
        event.handled = True
        if event.data2 > 0:
            if event.data1 == 70:
                if event.data2 == 1:
                    print('Channel Down')
                    PatIs = patterns.getPatternLength(patterns.patternNumber())
                    ui.showWindow(m.widChannelRack)
                    transport.globalTransport(m.FPT_Down, 1)
                    channelIs = channels.channelNumber() + 1
                    mixer.deselectAll()
                elif event.data2 == 127:
                    print('Channel Up')
                    PatIs = patterns.getPatternLength(patterns.patternNumber())
                    ui.showWindow(m.widChannelRack)
                    transport.globalTransport(m.FPT_Up, 1)
                    channelIsU = channels.channelNumber() - 1
                    mixer.deselectAll()

            elif event.data1 == 75:
                ui.showWindow(m.widBrowser)
                if event.data2 == 1:
                    print('DownBrowser')
                    transport.globalTransport(m.FPT_Down, 1)
                    time.sleep(0.01)
                elif event.data2 == 127:
                    print('UpBrowser')
                    transport.globalTransport(m.FPT_Up, 1)
                    time.sleep(0.01)

            elif event.data1 == 73:
                if ui.getFocused(1) or ui.getFocused(5):  # Pitch infocus with Channels
                    if event.data2 <= 63:
                        channels.setChannelPitch(channels.channelNumber(),
                                                 channels.getChannelPitch(channels.channelNumber()) + 0.005)
                        print('set +pitch')
                    elif event.data2 >= 64:
                        channels.setChannelPitch(channels.channelNumber(),
                                                 channels.getChannelPitch(channels.channelNumber()) - 0.005)
                        print('set -pitch')
                elif ui.getFocused(0):  # Tempo infocus with Mixer
                    if 1 <= event.data2 <= 63:
                        print('Tempo UP')
                        transport.globalTransport(m.FPT_TempoJog, 10)
                    elif 64 <= event.data2 <= 127:
                        print('Tempo DOWN')
                        transport.globalTransport(m.FPT_TempoJog, -10)

            elif event.data1 == 71:
                if ui.getFocused(1) or ui.getFocused(5):  # Volume infocus with Channels
                    if event.data2 <= 63:
                        channels.setChannelVolume(channels.channelNumber(),
                                                  channels.getChannelVolume(channels.channelNumber()) + 0.015)
                        print('set +vol')
                    elif event.data2 >= 64:
                        channels.setChannelVolume(channels.channelNumber(),
                                                  channels.getChannelVolume(channels.channelNumber()) - 0.015)
                        print('set -vol')
                elif ui.getFocused(0) or ui.getFocused(5):  # Volume infocus with Mixer
                    if event.data2 <= 63:
                        print('Mixvolume')
                        mixer.setTrackVolume(mixer.trackNumber(), mixer.getTrackVolume(mixer.trackNumber()) + 0.010)
                    elif event.data2 >= 64:
                        print('Mixvolume')
                        mixer.setTrackVolume(mixer.trackNumber(), mixer.getTrackVolume(mixer.trackNumber()) - 0.010)

            elif event.data1 == 72:
                if ui.getFocused(1) or ui.getFocused(5):  # PAN infocus with Channels
                    if event.data2 <= 63:
                        channels.setChannelPan(channels.channelNumber(),
                                               channels.getChannelPan(channels.channelNumber()) + 0.015)
                        print('set +pan')
                    elif event.data2 >= 64:
                        channels.setChannelPan(channels.channelNumber(),
                                               channels.getChannelPan(channels.channelNumber()) - 0.015)
                        print('set -pan')
                elif ui.getFocused(0) or ui.getFocused(5):  # PAN infocus with Mixer
                    if event.data2 <= 63:
                        mixer.setTrackPan(mixer.trackNumber(), mixer.getTrackPan(mixer.trackNumber()) + 0.015)
                        print('set +pan')
                    elif event.data2 >= 64:
                        mixer.setTrackPan(mixer.trackNumber(), mixer.getTrackPan(mixer.trackNumber()) - 0.015)
                        print('set -pan')

            elif event.data1 == 24:
                event.handled = True
                transport.globalTransport(m.FPT_F5, 64)
                print('Playlist')

            elif event.data1 == 28:
                event.handled = True
                transport.globalTransport(m.FPT_F7, 66)
                print('Pianoroll')

            elif event.data1 == 19:
                if ui.getFocused(0):
                    ui.setFocused(1)
                elif ui.getFocused(1):
                    ui.setFocused(4)
                elif ui.getFocused(4):
                    ui.setFocused(1)

                time.sleep(0.2)
                transport.globalTransport(m.FPT_Menu, 90)
                time.sleep(0.01)
                ui.setFocused(4)
                print('ADD Effect/Stuff Shortcut')

            elif event.data1 == 20:
                if not channels.isChannelSelected(channels.channelNumber()):
                    event.handled = True
                    transport.globalTransport(m.FPT_NextMixerWindow, 2)
                    print('NextMixerWindow')
                elif channels.isChannelSelected(channels.channelNumber()):
                    event.handled = True
                    channels.showCSForm(channels.channelNumber(), 1)
                    print('Show Channel Strip')

            elif event.data1 == 21:
                event.handled = True
                print('Menu')
                transport.globalTransport(m.FPT_ItemMenu, 91)

            elif event.data1 == 25:
                event.handled = True
                Pat = patterns.patternNumber() - 1
                patterns.jumpToPattern(Pat)
                print('Pattern-1')

            elif event.data1 == 29:
                event.handled = True
                Pat = patterns.patternNumber() + 1
                patterns.jumpToPattern(Pat)
                print('Pattern+1')

            elif event.data1 == 18:
                if ui.getFocused(1):
                    channelIs = channels.channelNumber()
                    print('Solo Channel:', channelIs)
                    channels.soloChannel(channelIs)
                elif ui.getFocused(0):
                    event.handled = True
                    trackNumberIs = mixer.trackNumber()
                    mixer.soloTrack(trackNumberIs)
                    print('Solo Track')
                elif ui.getFocused(2):
                    f = patterns.patternNumber()
                    print('Performance STOP current pattern:', f)
                    track = f  # Select the number of your track
                    block = -1  # BlockId = -1 is the track name
                    playlist.triggerLiveClip(track, block, m.TLC_Fill)

            elif event.data1 == 22:
                if ui.getFocused(1):
                    channelIs = channels.channelNumber()
                    print('Mute Channel:', channelIs)
                    channels.muteChannel(channelIs)
                elif ui.getFocused(0):
                    event.handled = True
                    channelIs = mixer.trackNumber()
                    mixer.muteTrack(channelIs)
                    print('Mute Track')
                elif ui.getFocused(2):
                    f = patterns.patternNumber()
                    print('Performance LAUNCH current pattern:', f)
                    track = f  # Select the number of your track
                    block = 0  # BlockId = -1 is the track name
                    playlist.triggerLiveClip(track, block, m.TLC_Fill)

            elif event.data1 == 23:
                if 0 <= event.data2 <= 110:
                    print('ESCAPE')
                    transport.globalTransport(m.FPT_Escape, 81)
                elif 111 <= event.data2 <= 127:
                    print('ESCAPE ALL')
                    transport.globalTransport(m.FPT_F12, 71)

            elif event.data1 == 16:
                print('enter')
                transport.globalTransport(m.FPT_Enter, 80)

            elif event.data1 == 17:
                if ui.getFocused(0):
                    print('Menu2')
                    transport.globalTransport(m.FPT_Menu, 90)
                elif ui.getFocused(1):
                    print('pluginpicker')
                    m = channels.channelNumber()
                    f1 = channels.getTargetFxTrack(m)
                    mixer.setTrackNumber(f1)
                    transport.globalTransport(m.FPT_F8, 67)

            elif event.data1 == 26:
                transport.globalTransport(m.FPT_F4, 100)
                time.sleep(0.01)
                transport.globalTransport(m.FPT_Escape, 81)

            elif event.data1 == 31:
                transport.globalTransport(m.FPT_Copy, 51)
                print('Copy Pattern')

            elif event.data1 == 27:
                transport.globalTransport(m.FPT_Paste, 52)
                print('Paste Pattern')

            elif event.data1 == 30:
                print('selectallchannels')
                channels.selectAll()

            elif event.data1 == 74:
                if event.data2 == 1:
                    print('next on mixer')
                    ui.showWindow(m.widMixer)
                    ui.next()
                    time.sleep(0.01)
                    channels.deselectAll()
                elif event.data2 == 127:
                    print('previous on mixer')
                    ui.showWindow(m.widMixer)
                    ui.previous()
                    time.sleep(0.01)
                    channels.deselectAll()

            elif event.data1 == 77:
                if ui.getFocused(1):  # SetMixerRack infocus with Channels
                    if 1 <= event.data2 <= 63 and 0 < channels.getTargetFxTrack(channels.channelNumber()) < 125:
                        print('ChangeFXTrack+1')
                        m = channels.channelNumber()
                        channels.processRECEvent(channels.getRecEventId(m) + m.REC_Chan_FXTrack,
                                                 channels.getTargetFxTrack(m) + 1, m.REC_Control | m.REC_UpdateControl)
                    elif 64 <= event.data2 <= 127 and 0 < channels.getTargetFxTrack(channels.channelNumber()) < 125:
                        print('ChangeFXTrack-1')
                        m = channels.channelNumber()
                        channels.processRECEvent(channels.getRecEventId(m) + m.REC_Chan_FXTrack,
                                                 channels.getTargetFxTrack(m) - 1, m.REC_Control | m.REC_UpdateControl)
                    elif 1 <= event.data2 <= 63 and channels.getTargetFxTrack(channels.channelNumber()) == 0:
                        print('ChangeFXTrack+1')
                        m = channels.channelNumber()
                        channels.processRECEvent(channels.getRecEventId(m) + m.REC_Chan_FXTrack,
                                                 channels.getTargetFxTrack(m) + 1, m.REC_Control | m.REC_UpdateControl)
                    elif 64 <= event.data2 <= 127 and channels.getTargetFxTrack(channels.channelNumber()) == 125:
                        print('ChangeFXTrack-1')
                        m = channels.channelNumber()
                        channels.processRECEvent(channels.getRecEventId(m) + m.REC_Chan_FXTrack,
                                                 channels.getTargetFxTrack(m) - 1, m.REC_Control | m.REC_UpdateControl)
                elif ui.getFocused(0):  # While focusing mixer
                    if event.data2 <= 63:
                        print('Mastervolume+')
                        mixer.setTrackVolume(0, mixer.getTrackVolume(0) + 0.010)
                    elif event.data2 >= 64:
                        print('Mastervolume-')
                        mixer.setTrackVolume(0, mixer.getTrackVolume(0) - 0.010)
                elif ui.getFocused(2):  # While focusing Playlist
                    if event.data2 <= 63:
                        Pat = patterns.patternNumber() + 1
                        print('Pattern+1')
                        patterns.jumpToPattern(Pat)
                    elif event.data2 >= 64:
                        Pat = patterns.patternNumber() - 1
                        print('Pattern-1')
                        patterns.jumpToPattern(Pat)
                elif ui.getFocused(5):
                    if 1 <= event.data2 <= 53:
                        print('Plugin Left')
                        transport.globalTransport(m.FPT_Right, 43)
                    elif 74 <= event.data2 <= 127:
                        print('Plugin Right')
                        transport.globalTransport(m.FPT_Left, 42)

            elif event.data1 == 76:
                if ui.getFocused(5):
                    if 1 <= event.data2 <= 63:
                        ui.next()
                        print('next')
                    elif 64 <= event.data2 <= 127:
                        ui.previous()
                        print('previous')
                elif not ui.getFocused(1) and not ui.getFocused(0) and not ui.getFocused(3):
                    if 1 <= event.data2 <= 53:
                        print('Left')
                        transport.globalTransport(m.FPT_Right, 43)
                    elif 74 <= event.data2 <= 127:
                        print('Right')
                        transport.globalTransport(m.FPT_Left, 42)

    if event.midiId == m.MIDI_PROGRAMCHANGE and event.midiChan == 12:  # FL CREATIVE PC

        event.handled = True
        color_mappings = {
            12: [
                ("RED", -65536),
                ("Crimson", -983041),
                ("Maroon", -8388608),
            ],
            13: [
                ("BLUE", -16776961),
                ("DodgerBlue", -16748544),
                ("Navy", -16777012),
            ],
            14: [
                ("Yellow", -256),
                ("Gold", -45952),
                ("GoldenRod", -29696),
            ],
            15: [
                ("Green", -16711936),
                ("Lime", -16711809),
                ("ForestGreen", -8388352),
            ],
            8: [
                ("Purple", -8388480),
                ("Indigo", -8388608),
                ("DarkViolet", -16777216),
            ],
            9: [
                ("Orange", -23296),
                ("DarkOrange", -35904),
                ("Coral", -128),
            ],
            10: [
                ("LightBlue", -16751002),
                ("SkyBlue", -16752762),
                ("DeepSkyBlue", -16761036),
            ],
            11: [
                ("Silver", -6250336),
                ("Gray", -8355712),
                ("DarkGray", -8421505),
            ],
        }
        triplicated_color_mappings = {}
        index = att.slot
        for key, colors in color_mappings.items():
            triplicated_colors = []
            for color_name, color_value in colors:
                triplicated_colors.append((color_name, color_value))
                triplicated_colors.append((color_name + "2", color_value))
                triplicated_colors.append((color_name + "3", color_value))
            triplicated_color_mappings[key] = triplicated_colors
        if event.data2 < 1:
            if not channels.isChannelSelected(channels.channelNumber()):  # While Focusing Mixer
                if event.data1 == 4:
                    mixer.setTrackNumber(1)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    channels.deselectAll()
                    print('MixerWindow1')
                elif event.data1 == 5:
                    mixer.setTrackNumber(2)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow2')
                elif event.data1 == 6:
                    mixer.setTrackNumber(3)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow3')
                elif event.data1 == 7:
                    mixer.setTrackNumber(4)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow4')
                elif event.data1 == 0:
                    mixer.setTrackNumber(5)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow5')
                elif event.data1 == 1:
                    mixer.setTrackNumber(6)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow6')
                elif event.data1 == 2:
                    mixer.setTrackNumber(7)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow7')
                elif event.data1 == 3:
                    mixer.setTrackNumber(8)
                    transport.globalTransport(m.FPT_NextMixerWindow, 1)
                    print('MixerWindow8')

            elif channels.isChannelSelected(channels.channelNumber()) and not ui.getFocused(2) and not ui.getFocused(3):
                if event.data1 in range(4, 8):
                    channel_index = event.data1 - 4
                    channels.selectOneChannel(channel_index)
                    channels.showCSForm(channels.channelNumber(channel_index), 1)
                    print('Focus Channel')

            elif ui.getFocused(3):  # While Focusing pianoRoll
                if event.data1 == 4:
                    transport.globalTransport(m.FPT_Undo, 20)
                    print('Redo')
                elif event.data1 == 5:
                    transport.globalTransport(m.FPT_UndoUp, 21)
                    print('Undo')
                elif event.data1 == 6:
                    transport.globalTransport(m.FPT_Cut, 50)
                    print('Cut')
                elif event.data1 == 7:
                    transport.globalTransport(m.FPT_Paste, 52)
                    print('Paste')
                elif event.data1 == 0:
                    transport.globalTransport(m.FPT_Delete, 54)
                    print('Delete')
                elif event.data1 == 1:
                    transport.globalTransport(m.FPT_Insert, 53)
                    print('Insert')
                elif event.data1 == 2:
                    transport.globalTransport(m.FPT_Copy, 51)
                    print('Copy')
                elif event.data1 == 3:
                    transport.globalTransport(m.FPT_SaveNew, 93)
                    print('SaveAS')

            elif not ui.getFocused(0) and not ui.getFocused(1) and not ui.getFocused(3) and not ui.getFocused(
                    5):  # While Focusing Anything but not Mixer, pianoRoll, plugins, or Channels
                if event.data1 == 4:
                    print('Pat/Song')
                    transport.setLoopMode()
                elif event.data1 == 5:
                    print('Play')
                    transport.start()
                elif event.data1 == 6:
                    print('Stop')
                    transport.stop()
                elif event.data1 == 7:
                    print('Record')
                    transport.record()
                elif event.data1 == 0:
                    print('WaitForInput')
                    transport.globalTransport(m.FPT_WaitForInput, 111)
                elif event.data1 == 1:
                    print('CountDown')
                    transport.globalTransport(m.FPT_CountDown, 115)
                elif event.data1 == 2:
                    print('Overdub')
                    transport.globalTransport(m.FPT_Overdub, 112)
                elif event.data1 == 3:
                    print('LoopRecord')
                    transport.globalTransport(m.FPT_LoopRecord, 113)

        if event.data1 in triplicated_color_mappings.keys():
            colors = triplicated_color_mappings[event.data1]
            print(att.slot)  # Calculate the index based on event.data1
            if ui.getFocused(1):
                event.handled = True
                channels.setChannelColor(channels.channelNumber(), colors[index][1])
                print(f'Change Color Channel {colors[index][0]}')
            elif ui.getFocused(0):
                event.handled = True
                mixer.setTrackColor(mixer.trackNumber(), colors[index][1])
                print(f'Change Color Track {colors[index][0]}')
            elif ui.getFocused(2):
                event.handled = True
                patterns.setPatternColor(patterns.patternNumber(), colors[index][1])
                print(f'Change Color pattern {colors[index][0]}')

            # Update the index for the next color set
        att.slot = (index + 3) % 9


slotsel = 0  # Initial value of slotsel attribute (can be changed)

slotSEL_calc_mapping = {
    0: 0,
    1: 8,
    2: 16,
    3: 24,
    4: 32,
    5: 40,
    6: 48,
    7: 56,
    8: 64,
    9: 72,
    10: 80,
    11: 88,
    12: 96,
    13: 104,
    14: 112,
    15: 120,
    16: 128,
    17: 136,
    18: 144,
    19: 152
}

slotSEL_calc = slotSEL_calc_mapping.get(slotsel, 0)


def change_slotsel(value):
    global slotsel, slotSEL_calc
    slotsel += value
    slotsel = max(0, min(19, slotsel))  # Limit the value to the range 0-9
    slotSEL_calc = slotSEL_calc_mapping.get(slotsel, 0)
    ui.setHintMsg(f"SEL SLOT {slotsel}")
    print("slotSEL_calc:", slotSEL_calc)  # Print the updated value of slotSEL_calc


def OnControlChange(event):
    if event.midiId == (m.MIDI_CONTROLCHANGE) and (event.midiChan == 13):  ## FL PLUG
        global slotSEL_calc  # Declare slotSEL_calc as a global variable
        global slotsel
        if event.data2 > -0:
            # Button 1
            if event.data1 == 20:
                change_slotsel(1)
            # Button 2
            if event.data1 == 16:
                change_slotsel(-1)
            if 70 <= event.data1 <= 77:  ## Controls and FX 1
                if plugins.isValid(channels.channelNumber()) == 0 and not ui.getFocused(6):  ## samplers
                    event.handled = True
                    if event.data1 == 70:
                        step = 1 if event.data2 >= 64 else -1
                        m = channels.channelNumber()
                        eventId = m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber())
                        newValue = channels.incEventValue(eventId, step)
                        general.processRECEvent(eventId, newValue, m.REC_UpdateValue | m.REC_UpdateControl)
                    elif event.data1 == 72:
                        step = 1 if event.data2 >= 64 else -1
                        m = channels.channelNumber()
                        eventId = m.REC_Chan_SwingMix + channels.getRecEventId(channels.channelNumber())
                        newValue = channels.incEventValue(eventId, step)
                        general.processRECEvent(eventId, newValue, m.REC_UpdateValue | m.REC_UpdateControl)
                    elif event.data1 == 71:
                        step = 1 if event.data2 >= 64 else -1
                        m = channels.channelNumber()
                        eventId = m.REC_Chan_FRes + channels.getRecEventId(channels.channelNumber())
                        newValue = channels.incEventValue(eventId, step)
                        general.processRECEvent(eventId, newValue, m.REC_UpdateValue | m.REC_UpdateControl)
                    elif event.data1 == 73:
                        step = 1 if event.data2 >= 64 else -1
                        m = channels.channelNumber()
                        eventId = m.REC_Chan_OfsFCut + channels.getRecEventId(channels.channelNumber())
                        newValue = channels.incEventValue(eventId, step)
                        general.processRECEvent(eventId, newValue, m.REC_UpdateValue | m.REC_UpdateControl)
                    elif event.data1 == 74:
                        step = 1 if event.data2 >= 64 else -1
                        m = channels.channelNumber()
                        eventId = m.REC_Chan_OfsFRes + channels.getRecEventId(channels.channelNumber())
                        newValue = channels.incEventValue(eventId, step)
                        general.processRECEvent(eventId, newValue, m.REC_UpdateValue | m.REC_UpdateControl)
                elif plugins.isValid(mixer.trackNumber(), 0) == 1 and ui.getFocused(6):  ##FXs
                    for i in range(70, 77):
                        slotFX = 0
                        AA1F = plugins.getParamValue(slotSEL_calc + event.data1 - 70, mixer.trackNumber(), slotFX)
                        apply = slotSEL_calc + event.data1 - 70
                        ##print(apply)
                        if ui.getFocused(6):
                            BCL1F = AA1F - 0.0025000
                            BCP1F = AA1F + 0.0025000
                            if BCP1F <= 1.016 and event.data2 >= 64:
                                plugins.getParamName(apply, mixer.trackNumber(), slotFX)
                                plugins.setParamValue(BCP1F, apply, mixer.trackNumber(), slotFX, -1)
                                ##print(plugins.getParamName(0, mixer.trackNumber(), slotFX))
                            if BCL1F >= -0.94 and event.data2 <= 63:
                                plugins.getParamName(apply, mixer.trackNumber(), slotFX)
                                plugins.setParamValue(BCL1F, apply, mixer.trackNumber(), slotFX, -1)
                ##                    print(apply)
                elif plugins.isValid(channels.channelNumber()) == 1 and not ui.getFocused(6):  ## Instruments
                    for i in range(70, 77):
                        apply = event.data1 - 70
                        if ui.getFocused(5):
                            plugin_num = (apply)
                            param_num = (apply + slotSEL_calc)
                            current_value = plugins.getParamValue(param_num, channels.channelNumber())
                            BCL3 = current_value - 0.0150000
                            BCP3 = current_value + 0.0150000

                            if BCP3 <= 1.016 and event.data2 >= 64:
                                plugins.getPluginName(channels.channelNumber())
                                plugins.getParamName(param_num, channels.channelNumber())
                                plugins.setParamValue(BCP3, param_num, channels.channelNumber(), -1)
                            elif BCL3 >= -0.94 and event.data2 <= 63:
                                plugins.getPluginName(channels.channelNumber())
                                plugins.getParamName(param_num, channels.channelNumber())
                                plugins.setParamValue(BCL3, param_num, channels.channelNumber(), -1)
                            ui.setHintMsg(plugins.getParamName(param_num, channels.channelNumber()))
                            event.handled = True
    if event.midiId == (m.MIDI_CONTROLCHANGE) and (event.midiChan == 9):  ##FL FPC CC
        event.handled = True
        if event.data2 > 0:  # NoteOn
            if event.data1 == 20:
                event.handled = True
                channels.midiNoteOn(0, 60, event.data2)
            if event.data1 == 21:
                event.handled = True
                channels.midiNoteOn(1, 60, event.data2)
            if event.data1 == 22:
                event.handled = True
                channels.midiNoteOn(2, 60, event.data2)
            if event.data1 == 23:
                event.handled = True
                channels.midiNoteOn(3, 60, event.data2)
            if event.data1 == 16:
                event.handled = True
                channels.midiNoteOn(4, 60, event.data2)
            if event.data1 == 17:
                event.handled = True
                channels.midiNoteOn(5, 60, event.data2)
            if event.data1 == 18:
                event.handled = True
                channels.midiNoteOn(6, 60, event.data2)
            if event.data1 == 19:
                event.handled = True
                channels.midiNoteOn(7, 60, event.data2)  ## CCA
            if event.data1 == 28:
                event.handled = True
                channels.midiNoteOn(8, 60, event.data2)
            if event.data1 == 29:
                event.handled = True
                channels.midiNoteOn(9, 60, event.data2)
            if event.data1 == 30:
                event.handled = True
                channels.midiNoteOn(10, 60, event.data2)
            if event.data1 == 31:
                event.handled = True
                channels.midiNoteOn(11, 60, event.data2)
            if event.data1 == 24:
                event.handled = True
                channels.midiNoteOn(12, 60, event.data2)
            if event.data1 == 25:
                event.handled = True
                channels.midiNoteOn(13, 60, event.data2)
            if event.data1 == 26:
                event.handled = True
                channels.midiNoteOn(14, 60, event.data2)
            if event.data1 == 27:
                event.handled = True
                channels.midiNoteOn(15, 60, event.data2)  ##CCB
        if event.data2 == 0:  # NoteOFF
            if event.data1 == 20:
                event.handled = True
                channels.midiNoteOn(0, 60, -1)
            if event.data1 == 21:
                event.handled = True
                channels.midiNoteOn(1, 60, -1)
            if event.data1 == 22:
                event.handled = True
                channels.midiNoteOn(2, 60, -1)
            if event.data1 == 23:
                event.handled = True
                channels.midiNoteOn(3, 60, -1)
            if event.data1 == 16:
                event.handled = True
                channels.midiNoteOn(4, 60, -1)
            if event.data1 == 17:
                event.handled = True
                channels.midiNoteOn(5, 60, -1)
            if event.data1 == 18:
                event.handled = True
                channels.midiNoteOn(6, 60, -1)
            if event.data1 == 19:
                event.handled = True
                channels.midiNoteOn(7, 60, -1)  ##CC A
            if event.data1 == 28:
                event.handled = True
                channels.midiNoteOn(8, 60, -1)
            if event.data1 == 29:
                event.handled = True
                channels.midiNoteOn(9, 60, -1)
            if event.data1 == 30:
                event.handled = True
                channels.midiNoteOn(10, 60, -1)
            if event.data1 == 31:
                event.handled = True
                channels.midiNoteOn(11, 60, -1)
            if event.data1 == 24:
                event.handled = True
                channels.midiNoteOn(12, 60, -1)
            if event.data1 == 25:
                event.handled = True
                channels.midiNoteOn(13, 60, -1)
            if event.data1 == 26:
                event.handled = True
                channels.midiNoteOn(14, 60, -1)
            if event.data1 == 27:
                event.handled = True
                channels.midiNoteOn(15, 60, -1)  ##CC B


'''    if (event.midiId == m.MIDI_CONTROLCHANGE) and (event.midiChan == 13):
        event.handled = False

# Chord user data (default)
nrOfChordNotes   = 5                    # Number of audible notes of majorChordNotes (min = 2, max = number of listmembers)
majorChordNotes  = [0,4,7,-12, 12]      # relative chord/sequence note numbers
majorChordDelays = [0,0,0,0,0]   # delta delays in msec for strumming chords/sequence


# Global variables with default values (don't change)
noteCounter = 0  # Counter for current note of chord
oldStatus = -1   # oldEvent, status
oldData1  = -1   # oldEvent, data1
oldData2  = -1   # oldEvent, data2

    
   
    
def OnMidiIn(event):
#   Pre filtering / changing of midi messages
#   Note On with value 0 --> Note Off 
#   Some midi controllers send a Note On message with a velocity of 0
#   instead of a Note off midi message
    if (event.status == m.MIDI_NOTEON) and (event.data2 == 0) and (event.midiChan == 13):
        event.status = m.MIDI_NOTEOFF
        event.data2 = 0

def OnNoteOn(event):
    if event.midiChan == 13:
        global nrOfChordNotes
        global majorChordNotes 
        global majorChordDelays
        global noteCounter
        global oldStatus
        global oldData1    
        global oldData2        
        majorChordRate = 30000 # repeating rate (dummy high value)    
        
        if (noteCounter == 0) : # direct note from midi controller
            oldStatus = event.status
            oldData1 = event.data1        
            oldData2 = event.data2                
            device.stopRepeatMidiEvent ()
            # prepare next midi Note On event (trigger)        
            device.repeatMidiEvent (event,majorChordDelays [0], majorChordRate) 
            event.handled = True  # surpress direct note from midi controller 
        else :
            event.status = oldStatus
            event.data1  = oldData1
            event.data2  = oldData2        
            device.stopRepeatMidiEvent ()
        
            # modify actual event (generated by last repeatMidiEvent)
            event.data1 = event.data1 + majorChordNotes [noteCounter - 1]
            # prepare next midi Note On event (trigger)
            if (noteCounter < nrOfChordNotes) :
               device.repeatMidiEvent (event,majorChordDelays [noteCounter], majorChordRate)
            # Show actual (sounding) chord note   
            print ('Note ' + str(noteCounter) + ' =     ' + str (event.data1) + ' (' + utils.GetNoteName(event.data1) + ')')        

        noteCounter = noteCounter + 1    
        if (noteCounter > nrOfChordNotes) : noteCounter = 0
  
def OnNoteOff(event):
    if event.midiChan == 13:
        global noteCounter
        global nrOfChordNotes
        
        device.stopRepeatMidiEvent ()
        
        # Inject midi note off channel messages (note on with velocity 0) 
        for noteCounter in range (nrOfChordNotes):
           noteNum = event.data1 + majorChordNotes [noteCounter]
           channels.midiNoteOn (channels.selectedChannel(), noteNum, 0)
           print ('NoteOff ' + str(noteCounter) + ' =  ' + str (noteNum) + ' (' + utils.GetNoteName(noteNum) + ')')                
           
        noteCounter = 0  
              
''''''ui.setHintMsg
                channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), ((-1) + m.REC_GetValue), m.REC_Control | m.REC_UpdateValue)
                channels.processRECEvent(channels.getRecEventId(m) + m.REC_Chan_OfsFCut, (channels.getRecEventId(m) + m.REC_GetValue), m.REC_Control | m.REC_UpdateValue)
                device.midiOutMsg(176, 12, 18, 120)
                device.midiOutMsg(m.MIDI_CONTROLCHANGE, 12, 22, 81)
                
                channels.setChannelColor(channels.channelNumber(),-6998990)# set channel red -13481835 dark blue -3286901 yellow -8733633 Green
elif event.data1 == 77:
                if event.data2 <= 63:
                    event.handled = True
                    print('fcut')
                    channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), 1, m.REC_GetValue) + 1 , m.REC_UpdateValue)
                elif event.data2 >= 64:
                    event.handled = True
                    print('fcut')
                    channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), 1, m.REC_GetValue) - 1 , m.REC_UpdateValue)

            if event.data1 == 8:
                event.handled = True
                transport.globalTransport(m.FPT_NextMixerWindow, 1)
                print('NextMixerWindow')
            if event.data1 == 9:
                event.handled = True
                transport.globalTransport(m.FPT_MixerWindowJog, 1)  
                print('MixerWindow')     
    
            if event.data1 == 74: 
                print('TEST')    
                channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), 0, m.REC_GetValue) + 0.001 , m.REC_UpdateValue)
if event.data1 == 74:
                if event.data2 <= 1:
                    ##channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), (+ m.FromMIDI_Max), m.REC_Control | m.REC_UpdateControl(0.05) | m.REC_FromMIDI)
                    general.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), (- (64 - int(event.data2))) if (event.data2 < 65) else (int(event.data2) - 63), m.REC_UpdateControl | m.REC_UpdateValue | m.REC_ShowHint)
                    print('set +cutoff')
                elif event.data2 >= 164:
                    channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), (- m.FromMIDI_Max), m.REC_Control | m.REC_UpdateControl(0.05) | m.REC_FromMIDI)
                    print('set -cutoff')
            if event.data1 == 20:
                channels.showCSForm(channels.channelNumber(), 1)
                print('showwindow')
            if event.data1 == 74:
                if event.data2 <= 1:
                    channels.setChannelVolume(channels.channelNumber(), channels.getChannelVolume(channels.channelNumber()) + 0.015)
                    print('set +cutoff')
                elif event.data2 >= 64:
                    channels.setChannelVolume(channels.channelNumber(), channels.getChannelVolume(channels.channelNumber()) - 0.015)
                    print('set -cutoff')
            if event.data1 == 75:
                if event.data2 <= 1:
                    channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), round((event.controlVal + 0.001) + m.FromMIDI_Max), m.REC_Control | m.REC_UpdateControl | m.REC_FromMIDI)
                    print('set +cutoff')
                elif event.data2 >= 64:
                    channels.processRECEvent(m.REC_Chan_FCut + channels.getRecEventId(channels.channelNumber()), round((event.controlVal - 0.001) - m.FromMIDI_Max), m.REC_Control | m.REC_UpdateControl | m.REC_FromMIDI)
                    print('set -cutoff')
                        if event.data1 == 122:
            if event.data2 <= 63:
                    channels.setChannelIndex(channels.channelNumber(), channels.getChannelIndex(channels.channelNumber()) + 1)
                    print('set +pan')
            elif event.data2 >= 64:
                    channels.setChannelIndex(channels.channelNumber(), channels.getChannelIndex(channels.channelNumber()) - 1)
                    print('set -pan')        '''
