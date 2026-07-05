// Automatically converted with https://github.com/TheLeerName/ShadertoyToFlixel

#pragma header

#define iResolution vec3(openfl_TextureSize, 0.)
uniform float iTime;
#define iChannel0 bitmap
#define texture flixel_texture2D

// end of ShadertoyToFlixel header

// Helper function to draw a 2D bounding box
float box(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    // Normalized pixel coordinates
    vec2 uv = (2.0 * fragCoord - iResolution.xy) / min(iResolution.x, iResolution.y);
    
    // Store original UVs for the falling blocks
    vec2 blockUV = uv;

    // --- 1. YOUR ORIGINAL BACKGROUND PLASMA ---
    for(float i = 1.0; i < 10.0; i++){
        uv.x += 0.6 / i * cos(i * 2.5 * uv.y + iTime);
        uv.y += 0.6 / i * cos(i * 1.5 * uv.x + iTime);
    }
    vec3 background = vec3(0.1) / abs(sin(iTime - uv.y - uv.x));
    
    // --- 2. FALLING 3D BLOCKS LOGIC ---
    vec3 blockLayer = vec3(0.0);
    float alpha = 0.0;
    
    // Loop to create 3 different falling blocks
    for(float i = 0.0; i < 3.0; i++) {
        // Unique timing and horizontal offset for each block
        float timeOffset = i * 2.5; 
        float localTime = mod(iTime + timeOffset, 10.0); 
        
        // Only show and drop the block in the first 4 seconds of the 10-second loop
        if (localTime < 4.0) {
            // Speed and positions
            float fallSpeed = 1.5;
            float startY = 1.5;
            float posX = -0.6 + i * 0.6; // Spread across the screen
            
            // Adjust position over time
            vec2 blockPos = blockUV - vec2(posX, startY - localTime * fallSpeed);
            
            // Alternating sizes between cubes and rectangles
            vec2 size = (mod(i, 2.0) == 0.0) ? vec2(0.15, 0.15) : vec2(0.1, 0.2);
            
            // Faux-3D Extrusion effect (Layering front and side panels)
            float frontCard = box(blockPos, size);
            float shadowCard = box(blockPos - vec2(0.04, -0.04), size);
            
            // Define shades of grey
            vec3 frontColor = vec3(0.6); // Light grey front face
            vec3 sideColor  = vec3(0.3); // Dark grey side face
            
            // Render the pseudo-3D shape
            if (frontCard < 0.0) {
                blockLayer = frontColor;
                alpha = 1.0;
            } else if (shadowCard < 0.0 && blockPos.x > -size.x && blockPos.y < size.y) {
                blockLayer = sideColor;
                alpha = 1.0;
            }
        }
    }

    // --- 3. MIX BACKGROUND AND BLOCKS ---
    vec3 finalColor = mix(background, blockLayer, alpha);
    fragColor = vec4(finalColor, texture(iChannel0, fragCoord / iResolution.xy).a);
}

void main() {
	mainImage(gl_FragColor, openfl_TextureCoordv*openfl_TextureSize);
}