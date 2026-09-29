// Copyright (C) 2025 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only

import QtQuick
import QtQuick3D
import QtQuick3D.Helpers.impl

SsgiEnvEffect {
    id: ssgiEffect

    property bool indirectLightEnabled: true
    property real indirectLightBoost: 4.0       // 1 - 100

    property real bufferSizeFactor: 0.5         // 0 - 1 (leave it at 0.5, generally)

    property bool simulatedBounceEnabled: false
    property real simulatedBounceFactor: 0.5    // 0 - 1

    property int sampleCount: 4      // 1 - 16
    property real sampleRadius: 0.1  // 0.001 - 4
    property int sliceCount: 4       // 1 - 8
    property real hitThickness: 0.5  // 0.001 - 4

    property int debugMode: 0 // internal; needs uncommenting ENABLE_DEBUG_MODE in all the shaders

    readonly property TextureInput indirectAndAoSampler: TextureInput {
        texture: Texture {}
    }

    readonly property TextureInput blurredIndirectAndAoSampler: TextureInput {
        texture: Texture {}
    }

    Buffer {
        id: indirectAndAoBuffer
        name: "indirectAndAoBuffer"
        sizeMultiplier: ssgiEffect.bufferSizeFactor
        format: Buffer.RGBA16F

    }

    Buffer {
        id: blurredIndirectAndAoBuffer
        name: "blurredIndirectAndAoBuffer"
        sizeMultiplier: ssgiEffect.bufferSizeFactor
        bufferFlags: Buffer.SceneLifetime // for simulatedBounce
        format: Buffer.RGBA16F
    }

    Shader {
        id: ssgiMainShader
        stage: Shader.Fragment
        shader: "qrc:/qtquick3d_helpers/shaders/ssgi_ssilvb.frag"
    }

    Shader {
        id: ssgiBlurDownShader
        stage: Shader.Fragment
        shader: "qrc:/qtquick3d_helpers/shaders/ssgi_dualfilterblur_down.frag"
    }

    Shader {
        id: ssgiBlurUpShader
        stage: Shader.Fragment
        shader: "qrc:/qtquick3d_helpers/shaders/ssgi_dualfilterblur_up.frag"
    }

    Shader {
        id: ssgiComposeShader
        stage: Shader.Fragment
        shader: "qrc:/qtquick3d_helpers/shaders/ssgi_compose.frag"
    }

    Pass {
        id: ssaoAndIndirectPass
        output: indirectAndAoBuffer
        shaders: ssgiMainShader
        commands: [
            // for simulatedBounce
            BufferInput {
                // because it is SceneLifetime, so here this is the result from the previous frame
                buffer: blurredIndirectAndAoBuffer
                sampler: "blurredIndirectAndAoSampler"
            }
        ]
    }

    // Kawase / dual filter blur
    // https://community.arm.com/cfs-file/__key/communityserver-blogs-components-weblogfiles/00-00-00-20-66/siggraph2015_2D00_mmg_2D00_marius_2D00_notes.pdf
    Buffer {
        id: tempBuffer1
        name: "tempBuffer1"
        sizeMultiplier: ssgiEffect.bufferSizeFactor * 0.5
        format: Buffer.RGBA16F
    }

    Buffer {
        id: tempBuffer2
        name: "tempBuffer2"
        sizeMultiplier: ssgiEffect.bufferSizeFactor * 0.5 * 0.5
        format: Buffer.RGBA16F
    }

    Pass {
        id: indirectLightBufferBlurDownInputTo1
        output: tempBuffer1
        shaders: ssgiBlurDownShader
        commands: [
            BufferInput {
                buffer: indirectAndAoBuffer
            }
        ]
    }
    Pass {
        id: indirectLightBufferBlurDown1To2
        output: tempBuffer2
        shaders: ssgiBlurDownShader
        commands: [
            BufferInput {
                buffer: tempBuffer1
            }
        ]
    }

    Pass {
        id: indirectLightBufferBlurUp2To1
        output: tempBuffer1
        shaders: ssgiBlurUpShader
        commands: [
            BufferInput {
                buffer: tempBuffer2
            }
        ]
    }
    Pass {
        id: indirectLightBufferBlurUp1ToOutput
        output: blurredIndirectAndAoBuffer
        shaders: ssgiBlurUpShader
        commands: [
            BufferInput {
                buffer: tempBuffer1
            }
        ]
    }

    Pass {
        id: ssgiCompositionPass
        shaders: ssgiComposeShader
        commands: [
            BufferInput {
                buffer: blurredIndirectAndAoBuffer
                sampler: "blurredIndirectAndAoSampler"
            }
        ]
    }

    passes:
        [ ssaoAndIndirectPass,
          indirectLightBufferBlurDownInputTo1, indirectLightBufferBlurDown1To2,
          indirectLightBufferBlurUp2To1, indirectLightBufferBlurUp1ToOutput,
          ssgiCompositionPass
        ]
}
