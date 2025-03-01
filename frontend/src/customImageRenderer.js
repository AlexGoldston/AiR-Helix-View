import { AbstractNodeProgram } from "sigma/rendering/webgl/programs/common/node";

const POINTS = 1;
const ATTRIBUTES = 4;

/**
 * Custom WebGL node program that renders nodes as images
 */
export default class NodeProgramImage extends AbstractNodeProgram {
  constructor(gl, renderer) {
    super(gl, renderer);

    this.texture = null;
    this.textureLocation = null;
    this.atlasLocation = null;

    // Vertex shader source
    const vertexShaderSource = `
      attribute vec2 a_position;
      attribute float a_size;
      attribute vec4 a_color;
      attribute float a_angle;
      
      uniform mat3 u_matrix;
      uniform float u_ratio;
      uniform float u_scale;
      
      varying vec4 v_color;
      varying float v_border;
      
      void main() {
        gl_Position = vec4(
          (u_matrix * vec3(a_position, 1)).xy,
          0,
          1
        );
        
        // Multiply by ratio of pixel size to program size
        gl_PointSize = a_size * u_ratio * u_scale;
        
        v_color = a_color;
      }
    `;

    // Fragment shader source
    const fragmentShaderSource = `
      precision mediump float;
      
      varying vec4 v_color;
      
      uniform sampler2D u_texture;
      
      void main() {
        // Circle shape
        vec2 coord = gl_PointCoord - vec2(0.5, 0.5);
        float distance = length(coord);
        
        if (distance > 0.5) {
          discard;
        } else {
          // Apply color
          gl_FragColor = v_color;
        }
      }
    `;

    this.textureImage = new Image();
    this.textureImage.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

    this.textureLoaded = false;
    this.textureImage.onload = () => {
      this.textureLoaded = true;
      this.loadTexture();
      this.renderer.refresh();
    };

    this.program = this.makeProgram(vertexShaderSource, fragmentShaderSource);

    // Initialize matrix uniform location
    this.matrixLocation = gl.getUniformLocation(this.program, "u_matrix");
    this.ratioLocation = gl.getUniformLocation(this.program, "u_ratio");
    this.scaleLocation = gl.getUniformLocation(this.program, "u_scale");
    this.textureLocation = gl.getUniformLocation(this.program, "u_texture");
  }

  loadTexture() {
    const gl = this.gl;
    
    // Create and bind texture
    if (!this.texture) {
      this.texture = gl.createTexture();
    }
    
    gl.bindTexture(gl.TEXTURE_2D, this.texture);
    
    // Set texture parameters
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    
    // Upload image data
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, this.textureImage);
  }

  makeProgram(vertexShaderSource, fragmentShaderSource) {
    const gl = this.gl;
    
    // Create the vertex shader
    const vertexShader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vertexShader, vertexShaderSource);
    gl.compileShader(vertexShader);
    
    // Create the fragment shader
    const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fragmentShader, fragmentShaderSource);
    gl.compileShader(fragmentShader);
    
    // Create the program
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    
    // Check if program creation failed
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Failed to link program:", gl.getProgramInfoLog(program));
      gl.deleteProgram(program);
      throw new Error("Failed to link program");
    }
    
    return program;
  }

  process(data, hidden, attributes) {
    const array = attributes;
    
    if (hidden) {
      array.fill(0);
      return array;
    }
    
    const x = data.x || 0;
    const y = data.y || 0;
    const size = data.size || 1;
    const color = data.color || [0, 0, 0, 1];
    
    array[0] = x;
    array[1] = y;
    array[2] = size;
    array[3] = floatColor(color);
    
    return array;
  }

  render(params) {
    const gl = this.gl;
    const program = this.program;
    
    // Bind program
    gl.useProgram(program);
    
    // Bind uniforms
    gl.uniformMatrix3fv(this.matrixLocation, false, params.matrix);
    gl.uniform1f(this.ratioLocation, params.ratio);
    gl.uniform1f(this.scaleLocation, params.scalingRatio);
    
    // Bind texture
    if (this.textureLoaded && this.texture) {
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.texture);
      gl.uniform1i(this.textureLocation, 0);
    }
    
    // Bind buffers
    gl.enableVertexAttribArray(0);
    gl.enableVertexAttribArray(1);
    gl.enableVertexAttribArray(2);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    
    // Configure attributes
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, ATTRIBUTES * Float32Array.BYTES_PER_ELEMENT, 0);
    gl.vertexAttribPointer(1, 1, gl.FLOAT, false, ATTRIBUTES * Float32Array.BYTES_PER_ELEMENT, 2 * Float32Array.BYTES_PER_ELEMENT);
    gl.vertexAttribPointer(2, 1, gl.FLOAT, false, ATTRIBUTES * Float32Array.BYTES_PER_ELEMENT, 3 * Float32Array.BYTES_PER_ELEMENT);
    
    // Draw
    gl.drawArrays(gl.POINTS, 0, params.nodeCount);
    
    // Cleanup
    gl.disableVertexAttribArray(0);
    gl.disableVertexAttribArray(1);
    gl.disableVertexAttribArray(2);
    gl.bindBuffer(gl.ARRAY_BUFFER, null);
  }
  
  // Required implementations
  allocate(capacity) {
    super.allocate(capacity);
    this.buffer = this.gl.createBuffer();
  }
  
  bind() {
    this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer);
  }
  
  bufferData() {
    this.gl.bufferData(this.gl.ARRAY_BUFFER, this.array, this.gl.DYNAMIC_DRAW);
  }
  
  hasNothingToRender() {
    return this.nodeIndices.length === 0;
  }
}

// Helper function to convert RGBA color to float
function floatColor(color) {
  return (
    (Math.floor(color[0] * 255) << 24) |
    (Math.floor(color[1] * 255) << 16) |
    (Math.floor(color[2] * 255) << 8) |
    Math.floor((color[3] !== undefined ? color[3] : 1) * 255)
  );
}