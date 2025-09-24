use slapi_rs::safe::*;
use std::path::Path;

fn main() -> Result<()> {
    // Initialize the SketchUp API
    let init_result = slapi_rs::initialize();
    if init_result != slapi_rs::SU_ERROR_NONE {
        return Err(SlapiError::new(init_result, "Failed to initialize SketchUp API"));
    }
    
    // Print SketchUp version info
    println!("SketchUp API Version: {}", slapi_rs::get_version());
    println!("Is Pro Edition: {}", slapi_rs::is_pro_edition());
    
    // Create a new model
    let model = Model::new()?;
    
    // Get the entities collection
    let entities = model.entities()?;
    
    // Create a cube with the safe wrapper
    create_cube(&entities, 10.0)?;
    
    // Check the number of faces and edges
    println!("Face count: {}", entities.face_count()?);
    println!("Edge count: {}", entities.edge_count()?);
    
    // Save the model
    let output_path = Path::new("safe_cube.skp");
    model.save(output_path)?;
    println!("Model saved to: {}", output_path.display());
    
    // The model will be automatically released when it goes out of scope
    
    // Terminate the SketchUp API
    slapi_rs::terminate();
    
    Ok(())
}

fn create_cube(entities: &Entities, size: f64) -> Result<()> {
    // Create a new geometry input
    let mut geom_input = GeometryInput::new()?;
    
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
    
    // Add vertices to the geometry input
    for vertex in &vertices {
        geom_input.add_vertex(vertex[0], vertex[1], vertex[2])?;
    }
    
    // Define the 6 faces of the cube
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
    
    // Add faces to the geometry input
    for face in &faces {
        geom_input.add_face(&[face[0] as u32, face[1] as u32, face[2] as u32, face[3] as u32])?;
    }
    
    // Fill the entities with the geometry
    entities.fill_from_geometry(&geom_input)?;
    
    // The geometry input will be automatically released when it goes out of scope
    
    Ok(())
} 