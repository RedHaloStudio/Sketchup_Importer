#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

//! Rust bindings for the SketchUp API.
//!
//! This crate provides Rust bindings to the native SketchUp C API (SLAPI).
//! It allows for creating, reading, and modifying SketchUp models programmatically.
//!
//! # Usage
//! 
//! ```no_run
//! use slapi_rs::safe::*;
//! 
//! fn main() -> Result<()> {
//!     // Initialize the SketchUp API
//!     slapi_rs::initialize();
//!     
//!     // Create a new model
//!     let model = Model::new()?;
//!     
//!     // Work with the model
//!     let entities = model.entities()?;
//!     println!("Face count: {}", entities.face_count()?);
//!     
//!     // Save the model
//!     model.save("example.skp")?;
//!     
//!     // Terminate the SketchUp API
//!     slapi_rs::terminate();
//!     
//!     Ok(())
//! }
//! ```

// Include the automatically generated bindings
pub mod bindings {
 include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}
//mod bindings;
mod safe;
mod error;

pub use safe::*;
pub use error::*;
pub use error::Result;
pub use error::SlapiError;

pub use bindings::SUResult;
pub use bindings::SUModelRef;
pub use bindings::SUEntitiesRef;
pub use bindings::SUGeometryInputRef;
pub use bindings::SUPoint3D;
pub use bindings::SUEntityRef;
pub use bindings::SUFaceRef;
pub use bindings::SUEdgeRef;
pub use bindings::SUComponentDefinitionRef;
pub use bindings::SUComponentInstanceRef;
pub use bindings::SUMaterialRef;
pub use bindings::SUTextureRef;
pub use bindings::SULayerRef;
pub use bindings::SUGroupRef;

/// Prelude module to import all commonly used types and functions
pub mod prelude {
    pub use super::{
        initialize, terminate, 
        SUResult,
        SUModelRef, SUEntitiesRef, SUEntityRef, SUFaceRef, SUEdgeRef,
        SUComponentDefinitionRef, SUComponentInstanceRef,
        SUMaterialRef, SUTextureRef, SULayerRef, SUGroupRef,
    };
    
    // Import safe wrappers
    pub use super::safe::{Model, Entities, GeometryInput};
    pub use super::error::{Result, SlapiError};
}

/// Initialize the SketchUp API.
///
/// This function should be called before any other SLAPI functions.
pub fn initialize() {
    unsafe { bindings::SUInitialize() }
}

/// Terminate the SketchUp API.
///
/// This function should be called when you're finished using the SLAPI.
pub fn terminate() {
    unsafe { bindings::SUTerminate() }
}

/// Get the SketchUp version as a string.
///
/// Returns a string containing the version information of the SketchUp API.
pub fn get_version() -> String {
    let mut version = [0u8; 64];
    let mut version_size = version.len();
    
    unsafe {
        bindings::SUGetVersionStringUtf8(version_size, version.as_mut_ptr() as *mut i8);
    }
    
    String::from_utf8_lossy(&version)
        .trim_end_matches('\0')
        .to_string()
}
