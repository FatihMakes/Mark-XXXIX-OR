__all__: list[str] = []

import cv2
import cv2.typing
import numpy
import os
import sys
import typing as _typing
if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


# Enumerations
AUTO_PAD_NONE: int
AUTO_PAD_SAME_UPPER: int
AUTO_PAD_SAME_LOWER: int
AUTO_PAD_VALID: int
AutoPadding = int
"""One of [AUTO_PAD_NONE, AUTO_PAD_SAME_UPPER, AUTO_PAD_SAME_LOWER, AUTO_PAD_VALID]"""

ACTIV_NONE: int
ACTIV_MISH: int
ACTIV_SWISH: int
ACTIV_SIGMOID: int
ACTIV_TANH: int
ACTIV_ELU: int
ACTIV_HARDSWISH: int
ACTIV_HARDSIGMOID: int
ACTIV_GELU: int
ACTIV_GELU_APPROX: int
ACTIV_RELU: int
ACTIV_CLIP: int
ActivationType = int
"""One of [ACTIV_NONE, ACTIV_MISH, ACTIV_SWISH, ACTIV_SIGMOID, ACTIV_TANH, ACTIV_ELU, ACTIV_HARDSWISH, ACTIV_HARDSIGMOID, ACTIV_GELU, ACTIV_GELU_APPROX, ACTIV_RELU, ACTIV_CLIP]"""

LOSS_REDUCTION_NONE: int
LOSS_REDUCTION_MEAN: int
LOSS_REDUCTION_SUM: int
LossReduction = int
"""One of [LOSS_REDUCTION_NONE, LOSS_REDUCTION_MEAN, LOSS_REDUCTION_SUM]"""

DNN_BACKEND_DEFAULT: int
DNN_BACKEND_INFERENCE_ENGINE: int
DNN_BACKEND_OPENCV: int
DNN_BACKEND_VKCOM: int
DNN_BACKEND_CUDA: int
DNN_BACKEND_WEBNN: int
DNN_BACKEND_TIMVX: int
DNN_BACKEND_CANN: int
Backend = int
"""One of [DNN_BACKEND_DEFAULT, DNN_BACKEND_INFERENCE_ENGINE, DNN_BACKEND_OPENCV, DNN_BACKEND_VKCOM, DNN_BACKEND_CUDA, DNN_BACKEND_WEBNN, DNN_BACKEND_TIMVX, DNN_BACKEND_CANN]"""

DNN_TARGET_CPU: int
DNN_TARGET_OPENCL: int
DNN_TARGET_OPENCL_FP16: int
DNN_TARGET_MYRIAD: int
DNN_TARGET_VULKAN: int
DNN_TARGET_FPGA: int
DNN_TARGET_CUDA: int
DNN_TARGET_CUDA_FP16: int
DNN_TARGET_HDDL: int
DNN_TARGET_NPU: int
DNN_TARGET_CPU_FP16: int
Target = int
"""One of [DNN_TARGET_CPU, DNN_TARGET_OPENCL, DNN_TARGET_OPENCL_FP16, DNN_TARGET_MYRIAD, DNN_TARGET_VULKAN, DNN_TARGET_FPGA, DNN_TARGET_CUDA, DNN_TARGET_CUDA_FP16, DNN_TARGET_HDDL, DNN_TARGET_NPU, DNN_TARGET_CPU_FP16]"""

DNN_TRACE_NONE: int
DNN_TRACE_ALL: int
DNN_TRACE_OP: int
TracingMode = int
"""One of [DNN_TRACE_NONE, DNN_TRACE_ALL, DNN_TRACE_OP]"""

DNN_PROFILE_NONE: int
DNN_PROFILE_SUMMARY: int
DNN_PROFILE_DETAILED: int
ProfilingMode = int
"""One of [DNN_PROFILE_NONE, DNN_PROFILE_SUMMARY, DNN_PROFILE_DETAILED]"""

DNN_MODEL_GENERIC: int
DNN_MODEL_ONNX: int
DNN_MODEL_TF: int
DNN_MODEL_TFLITE: int
ModelFormat = int
"""One of [DNN_MODEL_GENERIC, DNN_MODEL_ONNX, DNN_MODEL_TF, DNN_MODEL_TFLITE]"""

DNN_ARG_EMPTY: int
DNN_ARG_CONST: int
DNN_ARG_INPUT: int
DNN_ARG_OUTPUT: int
DNN_ARG_TEMP: int
DNN_ARG_PATTERN: int
ArgKind = int
"""One of [DNN_ARG_EMPTY, DNN_ARG_CONST, DNN_ARG_INPUT, DNN_ARG_OUTPUT, DNN_ARG_TEMP, DNN_ARG_PATTERN]"""

ENGINE_CLASSIC: int
ENGINE_NEW: int
ENGINE_AUTO: int
ENGINE_ORT: int
EngineType = int
"""One of [ENGINE_CLASSIC, ENGINE_NEW, ENGINE_AUTO, ENGINE_ORT]"""

DNN_PMODE_NULL: int
DNN_PMODE_CROP_CENTER: int
DNN_PMODE_LETTERBOX: int
ImagePaddingMode = int
"""One of [DNN_PMODE_NULL, DNN_PMODE_CROP_CENTER, DNN_PMODE_LETTERBOX]"""

SoftNMSMethod_SOFTNMS_LINEAR: int
SOFT_NMSMETHOD_SOFTNMS_LINEAR: int
SoftNMSMethod_SOFTNMS_GAUSSIAN: int
SOFT_NMSMETHOD_SOFTNMS_GAUSSIAN: int
SoftNMSMethod = int
"""One of [SoftNMSMethod_SOFTNMS_LINEAR, SOFT_NMSMETHOD_SOFTNMS_LINEAR, SoftNMSMethod_SOFTNMS_GAUSSIAN, SOFT_NMSMETHOD_SOFTNMS_GAUSSIAN]"""


Reduce2Layer_ReduceType_MAX: int
REDUCE2LAYER_REDUCE_TYPE_MAX: int
Reduce2Layer_ReduceType_MIN: int
REDUCE2LAYER_REDUCE_TYPE_MIN: int
Reduce2Layer_ReduceType_MEAN: int
REDUCE2LAYER_REDUCE_TYPE_MEAN: int
Reduce2Layer_ReduceType_SUM: int
REDUCE2LAYER_REDUCE_TYPE_SUM: int
Reduce2Layer_ReduceType_L1: int
REDUCE2LAYER_REDUCE_TYPE_L1: int
Reduce2Layer_ReduceType_L2: int
REDUCE2LAYER_REDUCE_TYPE_L2: int
Reduce2Layer_ReduceType_PROD: int
REDUCE2LAYER_REDUCE_TYPE_PROD: int
Reduce2Layer_ReduceType_SUM_SQUARE: int
REDUCE2LAYER_REDUCE_TYPE_SUM_SQUARE: int
Reduce2Layer_ReduceType_LOG_SUM: int
REDUCE2LAYER_REDUCE_TYPE_LOG_SUM: int
Reduce2Layer_ReduceType_LOG_SUM_EXP: int
REDUCE2LAYER_REDUCE_TYPE_LOG_SUM_EXP: int
Reduce2Layer_ReduceType = int
"""One of [Reduce2Layer_ReduceType_MAX, REDUCE2LAYER_REDUCE_TYPE_MAX, Reduce2Layer_ReduceType_MIN, REDUCE2LAYER_REDUCE_TYPE_MIN, Reduce2Layer_ReduceType_MEAN, REDUCE2LAYER_REDUCE_TYPE_MEAN, Reduce2Layer_ReduceType_SUM, REDUCE2LAYER_REDUCE_TYPE_SUM, Reduce2Layer_ReduceType_L1, REDUCE2LAYER_REDUCE_TYPE_L1, Reduce2Layer_ReduceType_L2, REDUCE2LAYER_REDUCE_TYPE_L2, Reduce2Layer_ReduceType_PROD, REDUCE2LAYER_REDUCE_TYPE_PROD, Reduce2Layer_ReduceType_SUM_SQUARE, REDUCE2LAYER_REDUCE_TYPE_SUM_SQUARE, Reduce2Layer_ReduceType_LOG_SUM, REDUCE2LAYER_REDUCE_TYPE_LOG_SUM, Reduce2Layer_ReduceType_LOG_SUM_EXP, REDUCE2LAYER_REDUCE_TYPE_LOG_SUM_EXP]"""

NaryEltwiseLayer_OPERATION_AND: int
NARY_ELTWISE_LAYER_OPERATION_AND: int
NaryEltwiseLayer_OPERATION_EQUAL: int
NARY_ELTWISE_LAYER_OPERATION_EQUAL: int
NaryEltwiseLayer_OPERATION_GREATER: int
NARY_ELTWISE_LAYER_OPERATION_GREATER: int
NaryEltwiseLayer_OPERATION_GREATER_EQUAL: int
NARY_ELTWISE_LAYER_OPERATION_GREATER_EQUAL: int
NaryEltwiseLayer_OPERATION_LESS: int
NARY_ELTWISE_LAYER_OPERATION_LESS: int
NaryEltwiseLayer_OPERATION_LESS_EQUAL: int
NARY_ELTWISE_LAYER_OPERATION_LESS_EQUAL: int
NaryEltwiseLayer_OPERATION_OR: int
NARY_ELTWISE_LAYER_OPERATION_OR: int
NaryEltwiseLayer_OPERATION_POW: int
NARY_ELTWISE_LAYER_OPERATION_POW: int
NaryEltwiseLayer_OPERATION_XOR: int
NARY_ELTWISE_LAYER_OPERATION_XOR: int
NaryEltwiseLayer_OPERATION_BITSHIFT: int
NARY_ELTWISE_LAYER_OPERATION_BITSHIFT: int
NaryEltwiseLayer_OPERATION_MAX: int
NARY_ELTWISE_LAYER_OPERATION_MAX: int
NaryEltwiseLayer_OPERATION_MEAN: int
NARY_ELTWISE_LAYER_OPERATION_MEAN: int
NaryEltwiseLayer_OPERATION_MIN: int
NARY_ELTWISE_LAYER_OPERATION_MIN: int
NaryEltwiseLayer_OPERATION_MOD: int
NARY_ELTWISE_LAYER_OPERATION_MOD: int
NaryEltwiseLayer_OPERATION_FMOD: int
NARY_ELTWISE_LAYER_OPERATION_FMOD: int
NaryEltwiseLayer_OPERATION_PROD: int
NARY_ELTWISE_LAYER_OPERATION_PROD: int
NaryEltwiseLayer_OPERATION_SUB: int
NARY_ELTWISE_LAYER_OPERATION_SUB: int
NaryEltwiseLayer_OPERATION_SUM: int
NARY_ELTWISE_LAYER_OPERATION_SUM: int
NaryEltwiseLayer_OPERATION_ADD: int
NARY_ELTWISE_LAYER_OPERATION_ADD: int
NaryEltwiseLayer_OPERATION_DIV: int
NARY_ELTWISE_LAYER_OPERATION_DIV: int
NaryEltwiseLayer_OPERATION_WHERE: int
NARY_ELTWISE_LAYER_OPERATION_WHERE: int
NaryEltwiseLayer_OPERATION_BITWISE_AND: int
NARY_ELTWISE_LAYER_OPERATION_BITWISE_AND: int
NaryEltwiseLayer_OPERATION_BITWISE_OR: int
NARY_ELTWISE_LAYER_OPERATION_BITWISE_OR: int
NaryEltwiseLayer_OPERATION_BITWISE_XOR: int
NARY_ELTWISE_LAYER_OPERATION_BITWISE_XOR: int
NaryEltwiseLayer_OPERATION = int
"""One of [NaryEltwiseLayer_OPERATION_AND, NARY_ELTWISE_LAYER_OPERATION_AND, NaryEltwiseLayer_OPERATION_EQUAL, NARY_ELTWISE_LAYER_OPERATION_EQUAL, NaryEltwiseLayer_OPERATION_GREATER, NARY_ELTWISE_LAYER_OPERATION_GREATER, NaryEltwiseLayer_OPERATION_GREATER_EQUAL, NARY_ELTWISE_LAYER_OPERATION_GREATER_EQUAL, NaryEltwiseLayer_OPERATION_LESS, NARY_ELTWISE_LAYER_OPERATION_LESS, NaryEltwiseLayer_OPERATION_LESS_EQUAL, NARY_ELTWISE_LAYER_OPERATION_LESS_EQUAL, NaryEltwiseLayer_OPERATION_OR, NARY_ELTWISE_LAYER_OPERATION_OR, NaryEltwiseLayer_OPERATION_POW, NARY_ELTWISE_LAYER_OPERATION_POW, NaryEltwiseLayer_OPERATION_XOR, NARY_ELTWISE_LAYER_OPERATION_XOR, NaryEltwiseLayer_OPERATION_BITSHIFT, NARY_ELTWISE_LAYER_OPERATION_BITSHIFT, NaryEltwiseLayer_OPERATION_MAX, NARY_ELTWISE_LAYER_OPERATION_MAX, NaryEltwiseLayer_OPERATION_MEAN, NARY_ELTWISE_LAYER_OPERATION_MEAN, NaryEltwiseLayer_OPERATION_MIN, NARY_ELTWISE_LAYER_OPERATION_MIN, NaryEltwiseLayer_OPERATION_MOD, NARY_ELTWISE_LAYER_OPERATION_MOD, NaryEltwiseLayer_OPERATION_FMOD, NARY_ELTWISE_LAYER_OPERATION_FMOD, NaryEltwiseLayer_OPERATION_PROD, NARY_ELTWISE_LAYER_OPERATION_PROD, NaryEltwiseLayer_OPERATION_SUB, NARY_ELTWISE_LAYER_OPERATION_SUB, NaryEltwiseLayer_OPERATION_SUM, NARY_ELTWISE_LAYER_OPERATION_SUM, NaryEltwiseLayer_OPERATION_ADD, NARY_ELTWISE_LAYER_OPERATION_ADD, NaryEltwiseLayer_OPERATION_DIV, NARY_ELTWISE_LAYER_OPERATION_DIV, NaryEltwiseLayer_OPERATION_WHERE, NARY_ELTWISE_LAYER_OPERATION_WHERE, NaryEltwiseLayer_OPERATION_BITWISE_AND, NARY_ELTWISE_LAYER_OPERATION_BITWISE_AND, NaryEltwiseLayer_OPERATION_BITWISE_OR, NARY_ELTWISE_LAYER_OPERATION_BITWISE_OR, NaryEltwiseLayer_OPERATION_BITWISE_XOR, NARY_ELTWISE_LAYER_OPERATION_BITWISE_XOR]"""


# Classes
class DictValue:
    # Functions
    @_typing.overload
    def __init__(self, i: int) -> None: ...
    @_typing.overload
    def __init__(self, p: float) -> None: ...
    @_typing.overload
    def __init__(self, s: str) -> None: ...

    def isInt(self) -> bool: ...

    def isString(self) -> bool: ...

    def isReal(self) -> bool: ...

    def getIntValue(self, idx: int = ...) -> int: ...

    def getRealValue(self, idx: int = ...) -> float: ...

    def getStringValue(self, idx: int = ...) -> str: ...


class Layer(cv2.Algorithm):
    blobs: _typing.Sequence[cv2.typing.MatLike]
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> str: ...
    @property
    def preferableTarget(self) -> int: ...

    # Functions
    @_typing.overload
    def finalize(self, inputs: _typing.Sequence[cv2.typing.MatLike], outputs: _typing.Sequence[cv2.typing.MatLike] | None = ...) -> _typing.Sequence[cv2.typing.MatLike]: ...
    @_typing.overload
    def finalize(self, inputs: _typing.Sequence[cv2.UMat], outputs: _typing.Sequence[cv2.UMat] | None = ...) -> _typing.Sequence[cv2.UMat]: ...

    def run(self, inputs: _typing.Sequence[cv2.typing.MatLike], internals: _typing.Sequence[cv2.typing.MatLike], outputs: _typing.Sequence[cv2.typing.MatLike] | None = ...) -> tuple[_typing.Sequence[cv2.typing.MatLike], _typing.Sequence[cv2.typing.MatLike]]: ...

    def outputNameToIndex(self, outputName: str) -> int: ...


class Net:
    # Functions
    def __init__(self) -> None: ...

    @classmethod
    @_typing.overload
    def readFromModelOptimizer(cls, xml: str | os.PathLike[str], bin: str | os.PathLike[str]) -> Net: ...
    @classmethod
    @_typing.overload
    def readFromModelOptimizer(cls, bufferModelConfig: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], bufferWeights: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]]) -> Net: ...

    def empty(self) -> bool: ...

    def dump(self) -> str: ...

    def dumpToFile(self, path: str | os.PathLike[str]) -> None: ...

    def dumpToPbtxt(self, path: str | os.PathLike[str]) -> None: ...

    def addLayer(self, name: str, type: str, dtype: int, params: cv2.typing.LayerParams) -> int: ...

    def addLayerToPrev(self, name: str, type: str, dtype: int, params: cv2.typing.LayerParams) -> int: ...

    def getLayerId(self, layer: str) -> int: ...

    def getLayerNames(self) -> _typing.Sequence[str]: ...

    @_typing.overload
    def getLayer(self, layerId: int) -> Layer: ...
    @_typing.overload
    def getLayer(self, layerName: str) -> Layer: ...
    @_typing.overload
    def getLayer(self, layerId: cv2.typing.LayerId) -> Layer: ...

    def connect(self, outPin: str, inpPin: str) -> None: ...

    def registerOutput(self, outputName: str, layerId: int, outputPort: int) -> int: ...

    def setInputsNames(self, inputBlobNames: _typing.Sequence[str]) -> None: ...

    def setInputShape(self, inputName: str, shape: cv2.typing.MatShape) -> None: ...

    @_typing.overload
    def forward(self, outputName: str = ...) -> cv2.typing.MatLike: ...
    @_typing.overload
    def forward(self, outputBlobs: _typing.Sequence[cv2.typing.MatLike] | None = ..., outputName: str = ...) -> _typing.Sequence[cv2.typing.MatLike]: ...
    @_typing.overload
    def forward(self, outputBlobs: _typing.Sequence[cv2.UMat] | None = ..., outputName: str = ...) -> _typing.Sequence[cv2.UMat]: ...
    @_typing.overload
    def forward(self, outBlobNames: _typing.Sequence[str], outputBlobs: _typing.Sequence[cv2.typing.MatLike] | None = ...) -> _typing.Sequence[cv2.typing.MatLike]: ...
    @_typing.overload
    def forward(self, outBlobNames: _typing.Sequence[str], outputBlobs: _typing.Sequence[cv2.UMat] | None = ...) -> _typing.Sequence[cv2.UMat]: ...

    def forwardAsync(self, outputName: str = ...) -> cv2.AsyncArray: ...

    def forwardAndRetrieve(self, outBlobNames: _typing.Sequence[str]) -> _typing.Sequence[_typing.Sequence[cv2.typing.MatLike]]: ...

    def setPreferableBackend(self, backendId: int) -> None: ...

    def setPreferableTarget(self, targetId: int) -> None: ...

    def finalizeNet(self) -> None: ...

    def setTracingMode(self, tracingMode: TracingMode) -> None: ...

    def getTracingMode(self) -> TracingMode: ...

    def setProfilingMode(self, profilingMode: ProfilingMode) -> None: ...

    def getProfilingMode(self) -> ProfilingMode: ...

    def getModelFormat(self) -> ModelFormat: ...

    @_typing.overload
    def setInput(self, blob: cv2.typing.MatLike, name: str = ..., scalefactor: float = ..., mean: cv2.typing.Scalar = ...) -> None: ...
    @_typing.overload
    def setInput(self, blob: cv2.UMat, name: str = ..., scalefactor: float = ..., mean: cv2.typing.Scalar = ...) -> None: ...

    @_typing.overload
    def setParam(self, layer: int, numParam: int, blob: cv2.typing.MatLike) -> None: ...
    @_typing.overload
    def setParam(self, layerName: str, numParam: int, blob: cv2.typing.MatLike) -> None: ...

    @_typing.overload
    def getParam(self, layer: int, numParam: int = ...) -> cv2.typing.MatLike: ...
    @_typing.overload
    def getParam(self, layerName: str, numParam: int = ...) -> cv2.typing.MatLike: ...

    def getUnconnectedOutLayers(self) -> _typing.Sequence[int]: ...

    def getUnconnectedOutLayersNames(self) -> _typing.Sequence[str]: ...

    def getLayerShapes(self, netInputShapes: _typing.Sequence[cv2.typing.MatShape], netInputTypes: _typing.Sequence[int], layerId: int) -> tuple[_typing.Sequence[cv2.typing.MatShape], _typing.Sequence[cv2.typing.MatShape]]: ...

    def getFLOPS(self, netInputShapes: _typing.Sequence[cv2.typing.MatShape], netInputTypes: _typing.Sequence[int]) -> int: ...

    def getLayerTypes(self) -> _typing.Sequence[str]: ...

    def getLayersCount(self, layerType: str) -> int: ...

    def getMemoryConsumption(self, netInputShapes: _typing.Sequence[cv2.typing.MatShape], netInputTypes: _typing.Sequence[int]) -> tuple[int, int]: ...

    def enableFusion(self, fusion: bool) -> None: ...

    def enableWinograd(self, useWinograd: bool) -> None: ...

    @_typing.overload
    def getPerfProfile(self) -> tuple[int, _typing.Sequence[float]]: ...
    @_typing.overload
    def getPerfProfile(self) -> tuple[_typing.Sequence[str], _typing.Sequence[str], _typing.Sequence[str]]: ...

    def enableKVCache(self) -> None: ...

    def disableKVCache(self) -> None: ...

    def resetKVCache(self) -> None: ...

    def printPerfProfile(self) -> None: ...


class Image2BlobParams:
    scalefactor: cv2.typing.Scalar
    size: cv2.typing.Size
    mean: cv2.typing.Scalar
    swapRB: bool
    ddepth: int
    datalayout: cv2.DataLayout
    paddingmode: ImagePaddingMode
    borderValue: cv2.typing.Scalar

    # Functions
    @_typing.overload
    def __init__(self) -> None: ...
    @_typing.overload
    def __init__(self, scalefactor: cv2.typing.Scalar, size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., ddepth: int = ..., datalayout: cv2.DataLayout = ..., mode: ImagePaddingMode = ..., borderValue: cv2.typing.Scalar = ...) -> None: ...

    def blobRectToImageRect(self, rBlob: cv2.typing.Rect, size: cv2.typing.Size) -> cv2.typing.Rect: ...

    def blobRectsToImageRects(self, rBlob: _typing.Sequence[cv2.typing.Rect], size: cv2.typing.Size) -> _typing.Sequence[cv2.typing.Rect]: ...


class Model:
    # Functions
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...
    @_typing.overload
    def __init__(self, network: Net) -> None: ...

    @_typing.overload
    def setInputSize(self, size: cv2.typing.Size) -> Model: ...
    @_typing.overload
    def setInputSize(self, width: int, height: int) -> Model: ...

    def setInputMean(self, mean: cv2.typing.Scalar) -> Model: ...

    def setInputScale(self, scale: cv2.typing.Scalar) -> Model: ...

    def setInputCrop(self, crop: bool) -> Model: ...

    def setInputSwapRB(self, swapRB: bool) -> Model: ...

    def setOutputNames(self, outNames: _typing.Sequence[str]) -> Model: ...

    def setInputParams(self, scale: float = ..., size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., crop: bool = ...) -> None: ...

    @_typing.overload
    def predict(self, frame: cv2.typing.MatLike, outs: _typing.Sequence[cv2.typing.MatLike] | None = ...) -> _typing.Sequence[cv2.typing.MatLike]: ...
    @_typing.overload
    def predict(self, frame: cv2.UMat, outs: _typing.Sequence[cv2.UMat] | None = ...) -> _typing.Sequence[cv2.UMat]: ...

    def setPreferableBackend(self, backendId: Backend) -> Model: ...

    def setPreferableTarget(self, targetId: Target) -> Model: ...

    def enableWinograd(self, useWinograd: bool) -> Model: ...


class ClassificationModel(Model):
    # Functions
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...
    @_typing.overload
    def __init__(self, network: Net) -> None: ...

    def setEnableSoftmaxPostProcessing(self, enable: bool) -> ClassificationModel: ...

    def getEnableSoftmaxPostProcessing(self) -> bool: ...

    @_typing.overload
    def classify(self, frame: cv2.typing.MatLike) -> tuple[int, float]: ...
    @_typing.overload
    def classify(self, frame: cv2.UMat) -> tuple[int, float]: ...


class KeypointsModel(Model):
    # Functions
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...
    @_typing.overload
    def __init__(self, network: Net) -> None: ...

    @_typing.overload
    def estimate(self, frame: cv2.typing.MatLike, thresh: float = ...) -> _typing.Sequence[cv2.typing.Point2f]: ...
    @_typing.overload
    def estimate(self, frame: cv2.UMat, thresh: float = ...) -> _typing.Sequence[cv2.typing.Point2f]: ...


class SegmentationModel(Model):
    # Functions
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...
    @_typing.overload
    def __init__(self, network: Net) -> None: ...

    @_typing.overload
    def segment(self, frame: cv2.typing.MatLike, mask: cv2.typing.MatLike | None = ...) -> cv2.typing.MatLike: ...
    @_typing.overload
    def segment(self, frame: cv2.UMat, mask: cv2.UMat | None = ...) -> cv2.UMat: ...


class DetectionModel(Model):
    # Functions
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...
    @_typing.overload
    def __init__(self, network: Net) -> None: ...

    def setNmsAcrossClasses(self, value: bool) -> DetectionModel: ...

    def getNmsAcrossClasses(self) -> bool: ...

    @_typing.overload
    def detect(self, frame: cv2.typing.MatLike, confThreshold: float = ..., nmsThreshold: float = ...) -> tuple[_typing.Sequence[int], _typing.Sequence[float], _typing.Sequence[cv2.typing.Rect]]: ...
    @_typing.overload
    def detect(self, frame: cv2.UMat, confThreshold: float = ..., nmsThreshold: float = ...) -> tuple[_typing.Sequence[int], _typing.Sequence[float], _typing.Sequence[cv2.typing.Rect]]: ...


class TextRecognitionModel(Model):
    # Functions
    @_typing.overload
    def __init__(self, network: Net) -> None: ...
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...

    def setDecodeType(self, decodeType: str) -> TextRecognitionModel: ...

    def getDecodeType(self) -> str: ...

    def setDecodeOptsCTCPrefixBeamSearch(self, beamSize: int, vocPruneSize: int = ...) -> TextRecognitionModel: ...

    def setVocabulary(self, vocabulary: _typing.Sequence[str]) -> TextRecognitionModel: ...

    def getVocabulary(self) -> _typing.Sequence[str]: ...

    @_typing.overload
    def recognize(self, frame: cv2.typing.MatLike) -> str: ...
    @_typing.overload
    def recognize(self, frame: cv2.UMat) -> str: ...
    @_typing.overload
    def recognize(self, frame: cv2.typing.MatLike, roiRects: _typing.Sequence[cv2.typing.MatLike]) -> _typing.Sequence[str]: ...
    @_typing.overload
    def recognize(self, frame: cv2.UMat, roiRects: _typing.Sequence[cv2.UMat]) -> _typing.Sequence[str]: ...


class TextDetectionModel(Model):
    # Functions
    @_typing.overload
    def detect(self, frame: cv2.typing.MatLike) -> tuple[_typing.Sequence[_typing.Sequence[cv2.typing.Point]], _typing.Sequence[float]]: ...
    @_typing.overload
    def detect(self, frame: cv2.UMat) -> tuple[_typing.Sequence[_typing.Sequence[cv2.typing.Point]], _typing.Sequence[float]]: ...
    @_typing.overload
    def detect(self, frame: cv2.typing.MatLike) -> _typing.Sequence[_typing.Sequence[cv2.typing.Point]]: ...
    @_typing.overload
    def detect(self, frame: cv2.UMat) -> _typing.Sequence[_typing.Sequence[cv2.typing.Point]]: ...

    @_typing.overload
    def detectTextRectangles(self, frame: cv2.typing.MatLike) -> tuple[_typing.Sequence[cv2.typing.RotatedRect], _typing.Sequence[float]]: ...
    @_typing.overload
    def detectTextRectangles(self, frame: cv2.UMat) -> tuple[_typing.Sequence[cv2.typing.RotatedRect], _typing.Sequence[float]]: ...
    @_typing.overload
    def detectTextRectangles(self, frame: cv2.typing.MatLike) -> _typing.Sequence[cv2.typing.RotatedRect]: ...
    @_typing.overload
    def detectTextRectangles(self, frame: cv2.UMat) -> _typing.Sequence[cv2.typing.RotatedRect]: ...


class TextDetectionModel_EAST(TextDetectionModel):
    # Functions
    @_typing.overload
    def __init__(self, network: Net) -> None: ...
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...

    def setConfidenceThreshold(self, confThreshold: float) -> TextDetectionModel_EAST: ...

    def getConfidenceThreshold(self) -> float: ...

    def setNMSThreshold(self, nmsThreshold: float) -> TextDetectionModel_EAST: ...

    def getNMSThreshold(self) -> float: ...


class TextDetectionModel_DB(TextDetectionModel):
    # Functions
    @_typing.overload
    def __init__(self, network: Net) -> None: ...
    @_typing.overload
    def __init__(self, model: str | os.PathLike[str], config: str | os.PathLike[str] = ...) -> None: ...

    def setBinaryThreshold(self, binaryThreshold: float) -> TextDetectionModel_DB: ...

    def getBinaryThreshold(self) -> float: ...

    def setPolygonThreshold(self, polygonThreshold: float) -> TextDetectionModel_DB: ...

    def getPolygonThreshold(self) -> float: ...

    def setUnclipRatio(self, unclipRatio: float) -> TextDetectionModel_DB: ...

    def getUnclipRatio(self) -> float: ...

    def setMaxCandidates(self, maxCandidates: int) -> TextDetectionModel_DB: ...

    def getMaxCandidates(self) -> int: ...


class Tokenizer:
    # Functions
    @classmethod
    def load(cls, model_config: str | os.PathLike[str]) -> Tokenizer: ...

    def encode(self, text: str) -> _typing.Sequence[int]: ...

    def decode(self, tokens: _typing.Sequence[int]) -> str: ...


class LayerProtocol(Protocol):
    # Functions
    def __init__(self, params: dict[str, DictValue], blobs: _typing.Sequence[cv2.typing.MatLike]) -> None: ...

    def getMemoryShapes(self, inputs: _typing.Sequence[_typing.Sequence[int]]) -> _typing.Sequence[_typing.Sequence[int]]: ...

    def forward(self, inputs: _typing.Sequence[cv2.typing.MatLike]) -> _typing.Sequence[cv2.typing.MatLike]: ...



# Functions
def NMSBoxes(bboxes: _typing.Sequence[cv2.typing.Rect2d], scores: _typing.Sequence[float], score_threshold: float, nms_threshold: float, eta: float = ..., top_k: int = ...) -> _typing.Sequence[int]: ...

def NMSBoxesBatched(bboxes: _typing.Sequence[cv2.typing.Rect2d], scores: _typing.Sequence[float], class_ids: _typing.Sequence[int], score_threshold: float, nms_threshold: float, eta: float = ..., top_k: int = ...) -> _typing.Sequence[int]: ...

def NMSBoxesRotated(bboxes: _typing.Sequence[cv2.typing.RotatedRect], scores: _typing.Sequence[float], score_threshold: float, nms_threshold: float, eta: float = ..., top_k: int = ...) -> _typing.Sequence[int]: ...

@_typing.overload
def blobFromImage(image: cv2.typing.MatLike, scalefactor: float = ..., size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., crop: bool = ..., ddepth: int = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImage(image: cv2.UMat, scalefactor: float = ..., size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., crop: bool = ..., ddepth: int = ...) -> cv2.typing.MatLike: ...

@_typing.overload
def blobFromImageWithParams(image: cv2.typing.MatLike, param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImageWithParams(image: cv2.UMat, param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImageWithParams(image: cv2.typing.MatLike, blob: cv2.typing.MatLike | None = ..., param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImageWithParams(image: cv2.UMat, blob: cv2.UMat | None = ..., param: Image2BlobParams = ...) -> cv2.UMat: ...

@_typing.overload
def blobFromImages(images: _typing.Sequence[cv2.typing.MatLike], scalefactor: float = ..., size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., crop: bool = ..., ddepth: int = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImages(images: _typing.Sequence[cv2.UMat], scalefactor: float = ..., size: cv2.typing.Size = ..., mean: cv2.typing.Scalar = ..., swapRB: bool = ..., crop: bool = ..., ddepth: int = ...) -> cv2.typing.MatLike: ...

@_typing.overload
def blobFromImagesWithParams(images: _typing.Sequence[cv2.typing.MatLike], param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImagesWithParams(images: _typing.Sequence[cv2.UMat], param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImagesWithParams(images: _typing.Sequence[cv2.typing.MatLike], blob: cv2.typing.MatLike | None = ..., param: Image2BlobParams = ...) -> cv2.typing.MatLike: ...
@_typing.overload
def blobFromImagesWithParams(images: _typing.Sequence[cv2.UMat], blob: cv2.UMat | None = ..., param: Image2BlobParams = ...) -> cv2.UMat: ...

def getAvailableTargets(be: Backend) -> _typing.Sequence[Target]: ...

def getInferenceEngineBackendType() -> str: ...

def getInferenceEngineCPUType() -> str: ...

def getInferenceEngineVPUType() -> str: ...

@_typing.overload
def imagesFromBlob(blob_: cv2.typing.MatLike, images_: _typing.Sequence[cv2.typing.MatLike] | None = ...) -> _typing.Sequence[cv2.typing.MatLike]: ...
@_typing.overload
def imagesFromBlob(blob_: cv2.typing.MatLike, images_: _typing.Sequence[cv2.UMat] | None = ...) -> _typing.Sequence[cv2.UMat]: ...

@_typing.overload
def readNet(model: str | os.PathLike[str], config: str | os.PathLike[str] = ..., framework: str = ..., engine: int = ...) -> Net: ...
@_typing.overload
def readNet(framework: str, bufferModel: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], bufferConfig: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]] = ..., engine: int = ...) -> Net: ...

@_typing.overload
def readNetFromModelOptimizer(xml: str | os.PathLike[str], bin: str | os.PathLike[str] = ...) -> Net: ...
@_typing.overload
def readNetFromModelOptimizer(bufferModelConfig: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], bufferWeights: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]]) -> Net: ...

@_typing.overload
def readNetFromONNX(onnxFile: str | os.PathLike[str], engine: int = ...) -> Net: ...
@_typing.overload
def readNetFromONNX(buffer: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], engine: int = ...) -> Net: ...

@_typing.overload
def readNetFromTFLite(model: str | os.PathLike[str], engine: int = ...) -> Net: ...
@_typing.overload
def readNetFromTFLite(bufferModel: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], engine: int = ...) -> Net: ...

@_typing.overload
def readNetFromTensorflow(model: str | os.PathLike[str], config: str | os.PathLike[str] = ..., engine: int = ..., extraOutputs: _typing.Sequence[str] = ...) -> Net: ...
@_typing.overload
def readNetFromTensorflow(bufferModel: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]], bufferConfig: numpy.ndarray[_typing.Any, numpy.dtype[numpy.uint8]] = ..., engine: int = ..., extraOutputs: _typing.Sequence[str] = ...) -> Net: ...

def readTensorFromONNX(path: str | os.PathLike[str]) -> cv2.typing.MatLike: ...

def releaseHDDLPlugin() -> None: ...

def resetMyriadDevice() -> None: ...

def setInferenceEngineBackendType(newBackendType: str) -> str: ...

def softNMSBoxes(bboxes: _typing.Sequence[cv2.typing.Rect], scores: _typing.Sequence[float], score_threshold: float, nms_threshold: float, top_k: int = ..., sigma: float = ..., method: SoftNMSMethod = ...) -> tuple[_typing.Sequence[float], _typing.Sequence[int]]: ...

def writeTextGraph(model: str | os.PathLike[str], output: str | os.PathLike[str]) -> None: ...


