function validatePathData(path) {
    try {
        // Use the schema validator to validate the path data
        const isValid = validator.validate_path(path);
        if (!isValid) {
            throw new Error("Invalid path data");
        }
        return true;
    } catch (error) {
        console.error("Path validation failed:", error);
        return false;
    }
}

function validateDrawingData(drawing) {
    // Validate the drawing data before processing
    if (!drawing || !drawing.path || !drawing.points || !drawing.path.length) {
        throw new Error("Invalid drawing data");
        return false;
    }
    return true;
}

function handleDrawingUpdate(drawing) {
    // Validate the drawing data before processing
    if (!validateDrawingData(drawing)) {
        showError("Invalid drawing data");
        return;
    }
    
    // Process the valid drawing data
    // ...existing code...
}

function handlePathUpdate(path) {
    // Validate the path data before processing
    if (!validatePathData(path)) {
        showError("Invalid path data");
        return;
    }
    
    // Process the valid path data
    // ...existing code...
}