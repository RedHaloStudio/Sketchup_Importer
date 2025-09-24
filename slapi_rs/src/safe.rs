//! Safe wrappers for the SketchUp API bindings.
//!
//! This module provides safe Rust wrappers around the raw FFI bindings.
//! These wrappers handle resource management and error handling.

use std::ffi::{CStr, CString};
use std::path::Path;
use std::ptr;

// Import from the crate root
use crate::*;
use crate::error::*;
// Import constants from bindings
use crate::bindings::SUResult::{SU_ERROR_NONE, SU_ERROR_INVALID_INPUT};

// Import specific types from bindings
use bindings::SUModelRef;
use bindings::SUEntitiesRef;
use bindings::SUGeometryInputRef;
use bindings::SUPoint3D;

/// Check if a result is successful and return an error if not
fn check_result(result: SUResult, message: &str) -> Result<()> {
    if result == SU_ERROR_NONE {
        Ok(())
    } else {
        Err(SlapiError::new(result, message))
    }
}

/// A safe wrapper for SUModelRef that automatically handles resource cleanup
pub struct Model {
    pub(crate) model_ref: SUModelRef,
    pub(crate) owned: bool,
}

impl Model {
    /// Create a new empty model
    pub fn new() -> Result<Self> {
        let mut model_ref = SUModelRef::default();
        let result = unsafe { crate::bindings::SUModelCreate(&mut model_ref) };
        check_result(result, "Failed to create model")?;
        
        Ok(Self {
            model_ref,
            owned: true,
        })
    }
    
    /// Open a model from a file
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path_str = path.as_ref().to_str()
            .ok_or_else(|| SlapiError::new(SU_ERROR_INVALID_INPUT, "Invalid path"))?;
        
        let path_cstr = CString::new(path_str)
            .map_err(|_| SlapiError::new(SU_ERROR_INVALID_INPUT, "Path contains null characters"))?;
        
        let mut model_ref = SUModelRef::default();
        let result = unsafe { crate::bindings::SUModelCreateFromFile(&mut model_ref, path_cstr.as_ptr()) };
        check_result(result, "Failed to open model file")?;
        
        Ok(Self {
            model_ref,
            owned: true,
        })
    }
    
    /// Get the active model from the SketchUp application
    pub fn active() -> Result<Self> {
        let mut model_ref = SUModelRef::default();
        let result = unsafe { crate::bindings::SUApplicationGetActiveModel(&mut model_ref) };
        check_result(result, "Failed to get active model")?;
        
        Ok(Self {
            model_ref,
            owned: false, // We don't own the active model, so we shouldn't release it
        })
    }
    
    /// Save the model to a file
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let path_str = path.as_ref().to_str()
            .ok_or_else(|| SlapiError::new(SU_ERROR_INVALID_INPUT, "Invalid path"))?;
        
        let path_cstr = CString::new(path_str)
            .map_err(|_| SlapiError::new(SU_ERROR_INVALID_INPUT, "Path contains null characters"))?;
        
        let result = unsafe { crate::bindings::SUModelSaveToFile(self.model_ref, path_cstr.as_ptr()) };
        check_result(result, "Failed to save model")
    }
    
    /// Get the entities collection from the model
    pub fn entities(&self) -> Result<Entities> {
        let mut entities_ref = SUEntitiesRef::default();
        let result = unsafe { crate::bindings::SUModelGetEntities(self.model_ref, &mut entities_ref) };
        check_result(result, "Failed to get entities")?;
        
        Ok(Entities {
            entities_ref,
            _model: self, // Keep a reference to the model to ensure it lives as long as the entities
        })
    }
}

impl Drop for Model {
    fn drop(&mut self) {
        if self.owned {
            unsafe {
                crate::bindings::SUModelRelease(&mut self.model_ref);
            }
        }
    }
}

/// A safe wrapper for SUEntitiesRef
pub struct Entities<'a> {
    pub(crate) entities_ref: SUEntitiesRef,
    _model: &'a Model, // Reference to the parent model to ensure it lives as long as the entities
}

impl<'a> Entities<'a> {
    /// Count the number of faces in the entities collection
    pub fn face_count(&self) -> Result<usize> {
        let mut count = 0;
        let result = unsafe { crate::bindings::SUEntitiesGetNumFaces(self.entities_ref, &mut count) };
        check_result(result, "Failed to get face count")?;
        
        Ok(count)
    }
    
    /// Count the number of edges in the entities collection
    pub fn edge_count(&self) -> Result<usize> {
        let mut count = 0;
        let result = unsafe { crate::bindings::SUEntitiesGetNumEdges(self.entities_ref, false, &mut count) };
        check_result(result, "Failed to get edge count")?;
        
        Ok(count)
    }
    
    /// Create entities from geometry input
    pub fn fill_from_geometry(&self, geom_input: &GeometryInput) -> Result<()> {
        let result = unsafe { crate::bindings::SUEntitiesFill(self.entities_ref, geom_input.geom_ref, true) };
        check_result(result, "Failed to fill entities with geometry")
    }
}

/// A safe wrapper for SUGeometryInputRef
pub struct GeometryInput {
    pub(crate) geom_ref: SUGeometryInputRef,
}

impl GeometryInput {
    /// Create a new geometry input object
    pub fn new() -> Result<Self> {
        let mut geom_ref = SUGeometryInputRef::default();
        let result = unsafe { crate::bindings::SUGeometryInputCreate(&mut geom_ref) };
        check_result(result, "Failed to create geometry input")?;
        
        Ok(Self { geom_ref })
    }
    
    /// Add a vertex to the geometry input
    pub fn add_vertex(&mut self, x: f64, y: f64, z: f64) -> Result<()> {
        let point = SUPoint3D { x, y, z };
        let result = unsafe { crate::bindings::SUGeometryInputAddVertex(self.geom_ref, &point) };
        check_result(result, "Failed to add vertex")
    }
    
    /// Add a face to the geometry input
    pub fn add_face(&mut self, indices: &[u32]) -> Result<()> {
        // Create a loop input
        let mut loop_input = bindings::SULoopInputRef::default();
        let result = unsafe { bindings::SULoopInputCreate(&mut loop_input) };
        check_result(result, "Failed to create loop input")?;
        
        // Add vertex indices to the loop
        for &index in indices {
            let result = unsafe { bindings::SULoopInputAddVertexIndex(loop_input, index as usize) };
            if result != SU_ERROR_NONE {
                // Clean up the loop input if there's an error
                unsafe { bindings::SULoopInputRelease(&mut loop_input) };
                return check_result(result, "Failed to add vertex index to loop");
            }
        }
        
        // Add the face with the loop
        let result = unsafe {
            bindings::SUGeometryInputAddFace(
                self.geom_ref,
                &mut loop_input,
                ptr::null_mut(),
            )
        };
        
        // If we get an error, we need to clean up the loop input ourselves
        if result != SU_ERROR_NONE {
            unsafe { bindings::SULoopInputRelease(&mut loop_input) };
        }
        
        check_result(result, "Failed to add face")
    }
}

impl Drop for GeometryInput {
    fn drop(&mut self) {
        unsafe {
            bindings::SUGeometryInputRelease(&mut self.geom_ref);
        }
    }
} 