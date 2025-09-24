use slapi_rs::prelude::*;
use std::path::Path;
use anyhow::{Context, Result};

fn main() -> Result<()> {
    // Initialize the SketchUp API
    slapi_rs::initialize();
    
    // Create a new, empty model
    let mut model = SUModelRef::default();
    unsafe { slapi_rs::bindings::SUModelCreate(&mut model) }.context("Failed to create model")?;
    
    // Get the entities collection from the model
    let mut entities = SUEntitiesRef::default();
    let result = unsafe { slapi_rs::SUModelGetEntities(model, &mut entities) };
    if result != SU_ERROR_NONE {
        return Err(format!("Failed to get entities: {}", result));
    }
    
    // Create a simple cube (6 faces)
    create_cube(&entities, 10.0)?;
    
    // Save the model to a file
    let output_path = Path::new("cube.skp");
    let output_path_str = output_path.to_str().unwrap();
    let result = unsafe {
        slapi_rs::SUModelSaveToFile(model, output_path_str.as_ptr() as *const i8)
    };
    
    if result != SU_ERROR_NONE {
        return Err(format!("Failed to save model: {}", result));
    }
    
    println!("Model saved to: {}", output_path.display());
    
    // Release the model
    unsafe {
        slapi_rs::SUModelRelease(&mut model);
    }
    
    // Terminate the SketchUp API
    slapi_rs::terminate();
    
    Ok(())
}

fn create_cube(entities: &SUEntitiesRef, size: f64) -> Result<()> {
    // Define the 8 vertices of the cube
    let half_size = size / 2.0;
    let vertices = [
        // Bottom face vertices
        [-half_size, -half_size, -half_size],
        [half_size, -half_size, -half_size],
        [half_size, half_size, -half_size],
        [-half_size, half_size, -half_size],
        // Top face vertices
        [-half_size, -half_size, half_size],
        [half_size, -half_size, half_size],
        [half_size, half_size, half_size],
        [-half_size, half_size, half_size],
    ];
    
    // Define the 6 faces of the cube by referencing vertex indices
    let faces = [
        // Bottom face (0,1,2,3)
        [0, 1, 2, 3],
        // Top face (4,5,6,7)
        [7, 6, 5, 4],
        // Front face (0,1,5,4)
        [0, 4, 5, 1],
        // Right face (1,2,6,5)
        [1, 5, 6, 2],
        // Back face (2,3,7,6)
        [2, 6, 7, 3],
        // Left face (3,0,4,7)
        [3, 7, 4, 0],
    ];
    
    // Create a geometry input object to define the cube geometry
    let mut geom_input = SUGeometryInputRef::default();
    let result = unsafe { slapi_rs::SUGeometryInputCreate(&mut geom_input) };
    if result != SU_ERROR_NONE {
        return Err(format!("Failed to create geometry input: {}", result));
    }
    
    // Add vertices to the geometry input
    for vertex in &vertices {
        let point3d = slapi_rs::SUPoint3D {
            x: vertex[0],
            y: vertex[1],
            z: vertex[2],
        };
        
        let result = unsafe { slapi_rs::SUGeometryInputAddVertex(geom_input, &point3d) };
        if result != SU_ERROR_NONE {
            return Err(format!("Failed to add vertex: {}", result));
        }
    }
    
    // Add faces to the geometry input
    for face in &faces {
        let mut face_indices = [0u32; 4];
        for (i, vertex_idx) in face.iter().enumerate() {
            face_indices[i] = *vertex_idx as u32;
        }
        
        let result = unsafe {
            slapi_rs::SUGeometryInputAddFace(
                geom_input,
                face_indices.len() as usize,
                face_indices.as_ptr(),
                std::ptr::null_mut(),
            )
        };
        
        if result != SU_ERROR_NONE {
            return Err(format!("Failed to add face: {}", result));
        }
    }
    
    // Create entities from the geometry input
    let result = unsafe { slapi_rs::SUEntitiesFill(*entities, geom_input, true) };
    if result != SU_ERROR_NONE {
        return Err(format!("Failed to fill entities: {}", result));
    }
    
    // Release the geometry input
    unsafe {
        slapi_rs::SUGeometryInputRelease(&mut geom_input);
    }
    
    Ok(())
} 