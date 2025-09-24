use crate::bindings::SUResult;

/// Error type for SketchUp API operations
#[derive(Debug)]
pub struct SlapiError {
    pub code: SUResult,
    pub message: String,
}

impl SlapiError {
    /// Create a new SlapiError with the given code and message
    pub fn new(code: SUResult, message: &str) -> Self {
        Self {
            code,
            message: message.to_string(),
        }
    }

    /// Convert a result code to a SlapiError with a default message
    pub fn from_result(code: SUResult) -> Self {
        let message = match code {
            SUResult::SU_ERROR_NONE => "No error",
            SUResult::SU_ERROR_NULL_POINTER_INPUT => "Null pointer input",
            SUResult::SU_ERROR_INVALID_INPUT => "Invalid input",
            SUResult::SU_ERROR_NULL_POINTER_OUTPUT => "Null pointer output",
            SUResult::SU_ERROR_INVALID_OUTPUT => "Invalid output",
            SUResult::SU_ERROR_OVERWRITE_VALID => "Overwrite valid",
            SUResult::SU_ERROR_GENERIC => "Generic error",
            SUResult::SU_ERROR_SERIALIZATION => "Serialization error",
            SUResult::SU_ERROR_OUT_OF_RANGE => "Out of range",
            SUResult::SU_ERROR_NO_DATA => "No data",
            SUResult::SU_ERROR_INSUFFICIENT_SIZE => "Insufficient size",
            SUResult::SU_ERROR_UNKNOWN_EXCEPTION => "Unknown exception",
            SUResult::SU_ERROR_MODEL_INVALID => "Model invalid",
            SUResult::SU_ERROR_MODEL_VERSION => "Model version error",
            SUResult::SU_ERROR_LAYER_LOCKED => "Layer locked",
            SUResult::SU_ERROR_DUPLICATE => "Duplicate",
            SUResult::SU_ERROR_PARTIAL_SUCCESS => "Partial success",
            SUResult::SU_ERROR_UNSUPPORTED => "Unsupported",
            SUResult::SU_ERROR_INVALID_ARGUMENT => "Invalid argument",
            _ => "Unknown error",
        };
        Self {
            code,
            message: message.to_string(),
        }
    }
}

impl std::fmt::Display for SlapiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "SketchUp API Error (code: {:?}): {}", self.code, self.message)
    }
}

impl std::error::Error for SlapiError {}

/// Type alias for Result with SlapiError
pub type Result<T> = std::result::Result<T, SlapiError>;

/// Convert a SUResult to a Result, with a custom error message if the operation failed
pub fn result_to_error<T>(result: SUResult, value: T, message: &str) -> Result<T> {
    if result == SUResult::SU_ERROR_NONE {
        Ok(value)
    } else {
        Err(SlapiError::new(result, message))
    }
}

/// Check if a result is successful and return an error if not
pub fn check_result(result: SUResult, message: &str) -> Result<()> {
    if result == SUResult::SU_ERROR_NONE {
        Ok(())
    } else {
        Err(SlapiError::new(result, message))
    }
}
