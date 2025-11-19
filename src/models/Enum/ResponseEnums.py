from enum import Enum


class ResponseSignals(Enum):
    FILE_NAME_CORRUPTED = "file_name_corrupted"
    FILE_VALIDATED_SUCCESS = "file_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOAD_SUCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_success"
    FILE_NO_CONTENT = "file_is_empty"
    NO_FILES_ERROR = "No file error"
    PROCESSING_FAILED = "processing_failed"
    PROCESSING_SUCCESS = "processing_sucess"
    PROECT_ID_NOT_EXIST = "project_id_not_exist"
    PRCOESS_REQUEST_FILE_ID_NOT_EXIST = "process_request_file_id_not_exist"

    ASSET_RECORD_NOT_VALID = "asset recort is not valid"
