from audioled import filtergraph
from audioled import audio
from audioled import devices
from audioled import colors
from audioled import audioreactive
from audioled import generative
from audioled import effects
from audioled import input
from audioled import panelize


def createMovingLightGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    audio_in = audio.AudioInput(num_channels=2)
    fg.addEffectNode(audio_in)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    color_wheel = colors.ColorWheel()
    fg.addEffectNode(color_wheel)

    movingLight = audioreactive.MovingLight(fs=audio_in.getSampleRate())
    fg.addEffectNode(movingLight)

    mirrorLower = effects.Mirror(mirror_lower=True, recursion=0)
    fg.addEffectNode(mirrorLower)

    afterglow = effects.AfterGlow(glow_time=0.15)
    fg.addEffectNode(afterglow)

    append = effects.Append(2, flip0=True)
    fg.addEffectNode(append)

    fg.addConnection(audio_in, 0, movingLight, 0)
    fg.addConnection(color_wheel, 0, movingLight, 1)
    fg.addConnection(movingLight, 0, afterglow, 0)
    fg.addConnection(afterglow, 0, append, 0)
    fg.addConnection(afterglow, 0, append, 1)
    fg.addConnection(append, 0, led_out, 0)

    return fg


def createMovingLightsGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    audio_in = audio.AudioInput(num_channels=2)
    fg.addEffectNode(audio_in)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    # Layer 1
    color_wheel1 = colors.ColorWheel()
    fg.addEffectNode(color_wheel1)

    movingLight1 = audioreactive.MovingLight(
        fs=audio_in.getSampleRate(), speed=150.0, dim_time=.5, highcut_hz=200)
    fg.addEffectNode(movingLight1)

    afterglow1 = effects.AfterGlow()
    fg.addEffectNode(afterglow1)

    append1 = effects.Append(2, flip0=True)
    fg.addEffectNode(append1)

    fg.addConnection(audio_in, 0, movingLight1, 0)
    fg.addConnection(color_wheel1, 0, movingLight1, 1)
    fg.addConnection(movingLight1, 0, afterglow1, 0)
    fg.addConnection(afterglow1, 0, append1, 0)
    fg.addConnection(afterglow1, 0, append1, 1)

    # Layer 2
    color_wheel2 = colors.ColorWheel()
    fg.addEffectNode(color_wheel2)

    movingLight2 = audioreactive.MovingLight(audio_in.getSampleRate(), speed=150.0, dim_time=1.0, highcut_hz=500)
    fg.addEffectNode(movingLight2)

    afterglow2 = effects.AfterGlow()
    fg.addEffectNode(afterglow2)

    append2 = effects.Append(2, flip1=True)
    fg.addEffectNode(append2)

    fg.addConnection(audio_in, 0, movingLight2, 0)
    fg.addConnection(color_wheel2, 0, movingLight2, 1)
    fg.addConnection(movingLight2, 0, afterglow2, 0)
    fg.addConnection(afterglow2, 0, append2, 0)
    fg.addConnection(afterglow2, 0, append2, 1)

    # Combine

    combine = effects.Combine(mode='lightenOnly')
    fg.addEffectNode(combine)

    fg.addConnection(append1, 0, combine, 0)
    fg.addConnection(append2, 0, combine, 1)
    fg.addConnection(combine, 0, led_out, 0)

    return fg


def createSpectrumGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    audio_in = audio.AudioInput(num_channels=2)
    fg.addEffectNode(audio_in)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    color_wheel = colors.ColorWheel()
    fg.addEffectNode(color_wheel)

    color_wheel2 = colors.ColorWheel(cycle_time=15.0)
    fg.addEffectNode(color_wheel2)

    spectrum = audioreactive.Spectrum(fs=audio_in.getSampleRate(), chunk_rate=60)
    fg.addEffectNode(spectrum)

    append = effects.Append(2, flip0=True)
    fg.addEffectNode(append)

    afterglow = effects.AfterGlow(glow_time=2.0)
    fg.addEffectNode(afterglow)

    fg.addConnection(audio_in, 0, spectrum, 0)
    fg.addConnection(color_wheel, 0, spectrum, 1)
    fg.addConnection(color_wheel2, 0, spectrum, 2)
    fg.addConnection(spectrum, 0, append, 0)
    fg.addConnection(spectrum, 0, append, 1)
    fg.addConnection(append, 0, afterglow, 0)
    fg.addConnection(afterglow, 0, led_out, 0)

    return fg


def createVUPeakGraph():

    fg = filtergraph.FilterGraph(recordTimings=True)

    audio_in = audio.AudioInput(num_channels=2)
    fg.addEffectNode(audio_in)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    color_wheel = colors.ColorWheel()
    fg.addEffectNode(color_wheel)

    color_wheel2 = colors.ColorWheel(cycle_time=5.0)
    fg.addEffectNode(color_wheel2)

    interpCol = colors.InterpolateHSV()
    fg.addEffectNode(interpCol)

    vu_peak = audioreactive.VUMeterPeak()
    fg.addEffectNode(vu_peak)

    vu_peak_R = audioreactive.VUMeterPeak()
    fg.addEffectNode(vu_peak_R)

    append = effects.Append(2, flip1=True)
    fg.addEffectNode(append)

    afterglow = effects.AfterGlow(0.5)
    fg.addEffectNode(afterglow)

    fg.addConnection(audio_in, 0, vu_peak, 0)
    fg.addConnection(color_wheel, 0, interpCol, 0)
    fg.addConnection(color_wheel2, 0, interpCol, 1)
    # fg.addConnection(interpCol,0,vu_peak,1)

    fg.addConnection(audio_in, 1, vu_peak_R, 0)
    # fg.addConnection(interpCol,0,vu_peak_R,1)

    fg.addConnection(vu_peak, 0, append, 0)
    fg.addConnection(vu_peak_R, 0, append, 1)
    fg.addConnection(append, 0, afterglow, 0)
    fg.addConnection(afterglow, 0, led_out, 0)
    return fg


def createSwimmingPoolGraph():

    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    color = colors.StaticRGBColor(55.0, 150.0, 236.0)
    fg.addEffectNode(color)

    SwimmingPool = generative.SwimmingPool()
    fg.addEffectNode(SwimmingPool)

    fg.addConnection(color, 0, SwimmingPool, 0)
    fg.addConnection(SwimmingPool, 0, led_out, 0)
    return fg


def createDefenceGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    Defence = generative.DefenceMode()
    fg.addEffectNode(Defence)

    fg.addConnection(Defence, 0, led_out, 0)
    return fg


def createKeyboardGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    PKeyboard = generative.MidiKeyboard()
    fg.addEffectNode(PKeyboard)

    fg.addConnection(PKeyboard, 0, led_out, 0)
    return fg


def createKeyboardSpringGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    PKeyboard = generative.MidiKeyboard()
    fg.addEffectNode(PKeyboard)

    color_wheel = colors.ColorWheel()
    fg.addEffectNode(color_wheel)

    springs = effects.SpringCombine()
    fg.addEffectNode(springs)

    fg.addConnection(PKeyboard, 0, springs, 0)
    fg.addConnection(springs, 0, led_out, 0)
    fg.addConnection(color_wheel, 0, springs, 1)
    fg.addConnection(color_wheel, 0, springs, 2)
    fg.addConnection(color_wheel, 0, springs, 3)
    return fg


def createProxyServerGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    candyIn = input.CandyServer()
    fg.addEffectNode(candyIn)

    fg.addConnection(candyIn, 0, led_out, 0)
    return fg


def createBreathingGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    Breathing = generative.Breathing()
    fg.addEffectNode(Breathing)

    fg.addConnection(Breathing, 0, led_out, 0)
    return fg


def createHeartbeatGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    Heartbeat = generative.Heartbeat()
    fg.addEffectNode(Heartbeat)

    fg.addConnection(Heartbeat, 0, led_out, 0)
    return fg


def createFallingStarsGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    FallingStars = generative.FallingStars()
    fg.addEffectNode(FallingStars)

    fg.addConnection(FallingStars, 0, led_out, 0)
    return fg


def createGifPlayerGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    gifPlayer = generative.GIFPlayer("gifs/nyancat.gif")
    fg.addEffectNode(gifPlayer)

    fg.addConnection(gifPlayer, 0, led_out, 0)

    return fg


def createPendulumGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    Pendulum = generative.Pendulum(heightactivator=False, displacement=.5)
    fg.addEffectNode(Pendulum)

    fg.addConnection(Pendulum, 0, led_out, 0)
    return fg


def createRPendulumGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    RPendulum = generative.RandomPendulums()
    fg.addEffectNode(RPendulum)

    fg.addConnection(RPendulum, 0, led_out, 0)
    return fg


def createTestBlobGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    TestBlob = generative.StaticBlob()
    fg.addEffectNode(TestBlob)

    fg.addConnection(TestBlob, 0, led_out, 0)
    return fg


def createBonfireGraph():

    fg = filtergraph.FilterGraph(recordTimings=True)

    audio_in = audio.AudioInput(num_channels=2)
    fg.addEffectNode(audio_in)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    bonfire = audioreactive.Bonfire(fs=audio_in.getSampleRate())
    fg.addEffectNode(bonfire)

    testblob = generative.StaticBlob()
    fg.addEffectNode(testblob)

    fg.addConnection(testblob, 0, bonfire, 1)
    fg.addConnection(audio_in, 0, bonfire, 0)

    fg.addConnection(bonfire, 0, led_out, 0)
    return fg


def createGenerateWavesGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    GenerateWaves = generative.GenerateWaves(wavemode='square')
    fg.addEffectNode(GenerateWaves)

    fg.addConnection(GenerateWaves, 0, led_out, 0)
    return fg


def createSortingGraph():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    Sorting = generative.Sorting()
    fg.addEffectNode(Sorting)

    fg.addConnection(Sorting, 0, led_out, 0)
    return fg


def createPanelPendulum():
    fg = filtergraph.FilterGraph(recordTimings=True)

    led_out = devices.LEDOutput()
    fg.addEffectNode(led_out)

    makeSquare = panelize.MakeSquare()
    fg.addEffectNode(makeSquare)

    pendulum = generative.Pendulum(heightactivator=False, displacement=0.5)
    fg.addEffectNode(pendulum)

    fg.addConnection(makeSquare, 0, led_out, 0)
    fg.addConnection(pendulum, 0, makeSquare, 0)
    return fg