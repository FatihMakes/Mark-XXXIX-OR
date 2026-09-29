__all__: list[str] = []

import cv2
import cv2.dnn
import cv2.typing
import typing as _typing


# Enumerations
MCC24: int
SG140: int
VINYL18: int
ColorChart = int
"""One of [MCC24, SG140, VINYL18]"""



# Classes
class CChecker(cv2.Algorithm):
    # Functions
    @classmethod
    def create(cls) -> CChecker: ...

    def setTarget(self, _target: ColorChart) -> None: ...

    def setBox(self, _box: _typing.Sequence[cv2.typing.Point2f]) -> None: ...

    def setChartsRGB(self, _chartsRGB: cv2.typing.MatLike) -> None: ...

    def setChartsYCbCr(self, _chartsYCbCr: cv2.typing.MatLike) -> None: ...

    def setCost(self, _cost: float) -> None: ...

    def setCenter(self, _center: cv2.typing.Point2f) -> None: ...

    def getTarget(self) -> ColorChart: ...

    def getBox(self) -> _typing.Sequence[cv2.typing.Point2f]: ...

    def getColorCharts(self) -> _typing.Sequence[cv2.typing.Point2f]: ...

    def getChartsRGB(self, getStats: bool = ...) -> cv2.typing.MatLike: ...

    def getChartsYCbCr(self) -> cv2.typing.MatLike: ...

    def getCost(self) -> float: ...

    def getCenter(self) -> cv2.typing.Point2f: ...


class DetectorParametersMCC:
    adaptiveThreshWinSizeMin: int
    adaptiveThreshWinSizeMax: int
    adaptiveThreshWinSizeStep: int
    adaptiveThreshConstant: float
    minContoursAreaRate: float
    minContoursArea: float
    confidenceThreshold: float
    minContourSolidity: float
    findCandidatesApproxPolyDPEpsMultiplier: float
    borderWidth: int
    B0factor: float
    maxError: float
    minContourPointsAllowed: int
    minContourLengthAllowed: int
    minInterContourDistance: int
    minInterCheckerDistance: int
    minImageSize: int
    minGroupSize: int

    # Functions
    def __init__(self) -> None: ...


class CCheckerDetector(cv2.Algorithm):
    # Functions
    @_typing.overload
    def processWithROI(self, image: cv2.typing.MatLike, regionsOfInterest: _typing.Sequence[cv2.typing.Rect], nc: int = ...) -> bool: ...
    @_typing.overload
    def processWithROI(self, image: cv2.UMat, regionsOfInterest: _typing.Sequence[cv2.typing.Rect], nc: int = ...) -> bool: ...

    @_typing.overload
    def process(self, image: cv2.typing.MatLike, nc: int = ...) -> bool: ...
    @_typing.overload
    def process(self, image: cv2.UMat, nc: int = ...) -> bool: ...

    def getBestColorChecker(self) -> CChecker: ...

    def getListColorChecker(self) -> _typing.Sequence[CChecker]: ...

    @classmethod
    @_typing.overload
    def create(cls) -> CCheckerDetector: ...
    @classmethod
    @_typing.overload
    def create(cls, net: cv2.dnn.Net) -> CCheckerDetector: ...

    @_typing.overload
    def draw(self, checkers: _typing.Sequence[CChecker], img: cv2.typing.MatLike, color: cv2.typing.Scalar = ..., thickness: int = ...) -> cv2.typing.MatLike: ...
    @_typing.overload
    def draw(self, checkers: _typing.Sequence[CChecker], img: cv2.UMat, color: cv2.typing.Scalar = ..., thickness: int = ...) -> cv2.UMat: ...

    def getRefColors(self) -> cv2.typing.MatLike: ...

    def setDetectionParams(self, params: DetectorParametersMCC) -> None: ...

    def setColorChartType(self, chartType: ColorChart) -> None: ...

    def setUseDnnModel(self, useDnn: bool) -> None: ...

    def getUseDnnModel(self) -> bool: ...

    def getDetectionParams(self) -> DetectorParametersMCC: ...

    def getColorChartType(self) -> ColorChart: ...



