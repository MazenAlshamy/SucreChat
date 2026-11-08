from fastapi import HTTPException, status


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": message})


def unauthorized(message: str = "يلزم بدء جلسة صالحة") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": message})


def forbidden(message: str = "ليست لديك صلاحية تنفيذ هذه العملية") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": message})


def not_found(message: str = "العنصر غير موجود") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": message})


def conflict(message: str, **extra) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": message, **extra})


def too_many(message: str = "تم تجاوز حد المحاولات، حاول لاحقاً") -> HTTPException:
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"message": message})


def service_unavailable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"message": message})
