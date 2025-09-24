use std::env;
use std::path::PathBuf;

fn main() {
    // Detect platform
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();
    
    // Get SDK path from environment or use default location
    let sdk_path = env::var("SKETCHUP_SDK_PATH").unwrap_or_else(|_| {
            String::from("..")
    });
    
    println!("cargo:rerun-if-changed=wrapper.h");
    println!("cargo:rerun-if-env-changed=SKETCHUP_SDK_PATH");
    
    // Set library linking instructions based on platform
    if target_os == "macos" {
        println!("cargo:rustc-link-search=framework={}", sdk_path);
        println!("cargo:rustc-link-lib=framework=SketchUpAPI");
    } else if target_os == "windows" {
        println!("cargo:rustc-link-search={}\\binaries\\sketchup\\x64", sdk_path);
        println!("cargo:rustc-link-lib=SketchUpAPI");
    } else {
        println!("cargo:rustc-link-search={}\\binaries\\sketchup\\x86_64", sdk_path);
        println!("cargo:rustc-link-lib=SketchUpAPI");
    }
    
    // Additional define for header search path
    let mut clang_args = vec!["-F", ".."];
    
    if target_os == "macos" {
        clang_args.extend_from_slice(&["-framework", "SketchUpAPI"]);
    }
    
    // Generate bindings using bindgen
    let bindings = bindgen::Builder::default()
        .header("wrapper.h")
        .clang_args(&clang_args)
        // Whitelist the SLAPI functions and types we want to use
        .allowlist_function("SU.*")
        .allowlist_type("SU.*")
        .allowlist_var("SU.*")
        // Block list these problematic types (if needed)
        // .blocklist_type("__darwin_.*")
        // Generate constified enums
        .rustified_enum("SUResult")
        .generate_comments(true)
        .prepend_enum_name(true)
        // Make the bindings derive common traits
        .derive_default(true)
        .derive_eq(true)
        .derive_hash(true)
        .derive_debug(true)
        // Generate bindings
        .generate()
        .expect("Unable to generate bindings");
    
    // Write bindings to output file
    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
} 