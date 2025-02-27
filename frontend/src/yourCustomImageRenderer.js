import { AbstractNodeProgram } from 'sigma/rendering';

export default class NodeProgramImage extends AbstractNodeProgram {
    constructor(gl, renderer) {
        super(gl, renderer);

        this.positionLocation = 0;
        this.colorLocation = 1;
        this.sizeLocation = 2;
        this.uvLocation = 3;
        this.matrixLocation = null;
        this.ratioLocation = null;
        this.scaleLocation = null;
        this.textureLocation = null;
        // NO this.texture here

        this.vertexShaderSource = `
        attribute vec2 a_position;
        attribute vec4 a_color;
        attribute float a_size;
        attribute vec2 a_uv;

        uniform mat3 u_matrix;
        uniform float u_ratio;
        uniform float u_scale;

        varying vec4 v_color;
        varying vec2 v_uv;

        void main() {
          gl_Position = vec4(
            (u_matrix * vec3(a_position, 1)).xy,
            0,
            1
          );

          gl_PointSize = a_size * u_ratio * u_scale;

          v_color = a_color;
          v_uv = a_uv;
        }
      `;

        this.fragmentShaderSource = `
        precision mediump float;

        varying vec4 v_color;
        varying vec2 v_uv;

        uniform sampler2D u_texture;

        void main() {
          gl_FragColor = texture2D(u_texture, v_uv) * v_color;
        }
      `;

        this.program = this.compile(this.vertexShaderSource, this.fragmentShaderSource);
    }

    compile(vertexSource, fragmentSource) {
        const gl = this.gl;

        const vertexShader = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vertexShader, vertexSource);
        gl.compileShader(vertexShader);

        if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
            console.error('An error occurred compiling the shaders: ' + gl.getShaderInfoLog(vertexShader));
            gl.deleteShader(vertexShader);
            return null;
        }

        const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fragmentShader, fragmentSource);
        gl.compileShader(fragmentShader);
        if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
            console.error('An error occurred compiling the shaders: ' + gl.getShaderInfoLog(fragmentShader));
            gl.deleteShader(fragmentShader);
            return null;
        }

        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error('Unable to initialize the shader program: ' + gl.getProgramInfoLog(program));
            return null;
        }
        return program;

    }

    process(data, hidden, attributes) {
      let texture = this.renderer.getNodeImageTexture(data.image);
      if (!texture) {
        texture = this.renderer.createNodeImageTexture(data.image);
      }

      if (hidden) {
          return {
              ...attributes,
              x: 0,
              y: 0,
              size: 0,
              color: [0, 0, 0, 0],
              uv: [0, 0, 0, 0, 0, 0, 0, 0],
          };
      }

      return {
          ...attributes,
          x: data.x,
          y: data.y,
          size: data.size,
          color: data.color || [0, 0, 0, 1], // Ensure color is an array
          uv: [0, 0, 1, 0, 0, 1, 1, 1],
      };
  }



  render(state) {
      if (!this.matrixLocation) {
          // Locations can only be queried after the program has been linked
          this.matrixLocation = this.gl.getUniformLocation(this.program, 'u_matrix');
          this.ratioLocation = this.gl.getUniformLocation(this.program, 'u_ratio');
          this.scaleLocation = this.gl.getUniformLocation(this.program, 'u_scale');
          this.textureLocation = this.gl.getUniformLocation(this.program, 'u_texture');
      }

      this.gl.useProgram(this.program);

      this.gl.uniformMatrix3fv(this.matrixLocation, false, state.matrix);
      this.gl.uniform1f(this.ratioLocation, state.ratio);
      this.gl.uniform1f(this.scaleLocation, state.scale);

      this.gl.enableVertexAttribArray(this.positionLocation);
      this.gl.enableVertexAttribArray(this.colorLocation);
      this.gl.enableVertexAttribArray(this.sizeLocation);
      this.gl.enableVertexAttribArray(this.uvLocation);

      this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.renderer.getNodeAttributesBuffer(this.constructor));
      this.gl.vertexAttribPointer(this.positionLocation, 2, this.gl.FLOAT, false, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 8, 0);
      this.gl.vertexAttribPointer(this.colorLocation, 4, this.gl.UNSIGNED_BYTE, true, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 8, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 2);
      this.gl.vertexAttribPointer(this.sizeLocation, 1, this.gl.FLOAT, false, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 8, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 6);
      this.gl.vertexAttribPointer(this.uvLocation, 2, this.gl.FLOAT, false, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 8, this.renderer.getNodeFloatAttributesBuffer().BYTES_PER_ELEMENT * 4);

      // Get the correct texture FOR THIS NODE from the renderer
      const texture = this.renderer.getNodeImageTexture(state.node.image); // Use getNodeImageTexture

        if (texture) {
        // Only bind and draw if the texture exists
            this.gl.activeTexture(this.gl.TEXTURE0); // Make sure we're using texture unit 0
            this.gl.bindTexture(this.gl.TEXTURE_2D, texture);
            this.gl.uniform1i(this.textureLocation, 0); // Tell the shader to use texture unit 0
            this.gl.drawArrays(this.gl.TRIANGLES, 0, this.renderer.getNodeCount());
      }
      this.gl.disableVertexAttribArray(this.positionLocation);
      this.gl.disableVertexAttribArray(this.colorLocation);
      this.gl.disableVertexAttribArray(this.sizeLocation);
      this.gl.disableVertexAttribArray(this.uvLocation);
  }
}