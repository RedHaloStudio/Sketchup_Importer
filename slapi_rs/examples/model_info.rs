use slapi_rs::prelude::*;
use std::path::Path;

fn main() -> Result<(), String> {
    // Initialize the SketchUp API
    let result = slapi_rs::initialize();
    if result != SU_ERROR_NONE {
        return Err(format!("Failed to initialize SketchUp API: {}", result));
    }
    
    // Print SketchUp version info
    println!("SketchUp API Version: {}", slapi_rs::get_version());
    println!("Is Pro Edition: {}", slapi_rs::is_pro_edition());
    
    // The path to your SketchUp model
    let model_path = Path::new("examples/model.skp");
    
    if model_path.exists() {
        // Create a reference to hold the model
        let mut model = SUModelRef::default();
        
        // Open the model file
        let model_path_str = model_path.to_str().unwrap();
        let result = unsafe {
            slapi_rs::SUModelCreateFromFile(&mut model, model_path_str.as_ptr() as *const i8)
        };
        
        if result == SU_ERROR_NONE {
            // Get entities from the model
            let mut entities = SUEntitiesRef::default();
            let result = unsafe {
                slapi_rs::SUModelGetEntities(model, &mut entities)
            };
            
            if result == SU_ERROR_NONE {
                // Count faces in the model
                let mut face_count = 0;
                let result = unsafe {
                    slapi_rs::SUEntitiesGetNumFaces(entities, &mut face_count)
                };
                
                if result == SU_ERROR_NONE {
                    println!("Number of faces in the model: {}", face_count);
                }
                
                // Count edges in the model
                let mut edge_count = 0;
                let result = unsafe {
                    slapi_rs::SUEntitiesGetNumEdges(entities, &mut edge_count)
                };
                
                if result == SU_ERROR_NONE {
                    println!("Number of edges in the model: {}", edge_count);
                }
            }
            
            // Close the model
            unsafe {
                slapi_rs::SUModelRelease(&mut model);
            }
        } else {
            eprintln!("Failed to open model file: {}", result);
        }
    } else {
        eprintln!("Model file does not exist: {}", model_path.display());
    }
    
    // Terminate the SketchUp API
    slapi_rs::terminate();
    
    Ok(())
} 