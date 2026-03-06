/**
 * Custom Sigma.js node program that renders square shapes.
 * Used for Summary and BehavioralPattern node types.
 *
 * Based on the NodeCircleProgram pattern: uses 3 vertices forming a large
 * triangle, then the fragment shader clips to a square using
 * Chebyshev distance (max(|x|, |y|) <= radius).
 */
import { NodeProgram } from 'sigma/rendering';
import type { NodeDisplayData, RenderParams } from 'sigma/types';
import { floatColor } from 'sigma/utils';

interface ProgramUniforms<U extends string> {
  gl: WebGLRenderingContext;
  uniformLocations: Record<U, WebGLUniformLocation>;
}

const { UNSIGNED_BYTE, FLOAT } = WebGLRenderingContext;

const VERTEX_SHADER = /* glsl */ `
attribute vec4 a_id;
attribute vec4 a_color;
attribute vec2 a_position;
attribute float a_size;
attribute float a_angle;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;

varying vec4 v_color;
varying vec2 v_diffVector;
varying float v_radius;

const float bias = 255.0 / 254.0;

void main() {
  float size = a_size * u_correctionRatio / u_sizeRatio * 4.0;
  vec2 diffVector = size * vec2(cos(a_angle), sin(a_angle));
  vec2 position = a_position + diffVector;
  gl_Position = vec4(
    (u_matrix * vec3(position, 1)).xy,
    0,
    1
  );

  v_diffVector = diffVector;
  v_radius = size / 2.0;

  #ifdef PICKING_MODE
  v_color = a_id;
  #else
  v_color = a_color;
  #endif

  v_color.a *= bias;
}
`;

const FRAGMENT_SHADER = /* glsl */ `
precision highp float;

varying vec4 v_color;
varying vec2 v_diffVector;
varying float v_radius;

uniform float u_correctionRatio;

const vec4 transparent = vec4(0.0, 0.0, 0.0, 0.0);

void main(void) {
  float border = u_correctionRatio * 2.0;
  // Chebyshev distance for square shape, scaled to fit within bounding triangle
  float halfSide = v_radius * 0.7071; // 1/sqrt(2) to inscribe square in circle
  float dist = max(abs(v_diffVector.x), abs(v_diffVector.y)) - halfSide + border;

  #ifdef PICKING_MODE
  if (dist > border)
    gl_FragColor = transparent;
  else
    gl_FragColor = v_color;
  #else
  float t = 0.0;
  if (dist > border)
    t = 1.0;
  else if (dist > 0.0)
    t = dist / border;

  gl_FragColor = mix(v_color, transparent, t);
  #endif
}
`;

const UNIFORMS = ['u_sizeRatio', 'u_correctionRatio', 'u_matrix'] as const;

const ANGLE_1 = 0;
const ANGLE_2 = (2 * Math.PI) / 3;
const ANGLE_3 = (4 * Math.PI) / 3;

export default class NodeSquareProgram extends NodeProgram<(typeof UNIFORMS)[number]> {
  getDefinition() {
    return {
      VERTICES: 3,
      VERTEX_SHADER_SOURCE: VERTEX_SHADER,
      FRAGMENT_SHADER_SOURCE: FRAGMENT_SHADER,
      METHOD: WebGLRenderingContext.TRIANGLES,
      UNIFORMS,
      ATTRIBUTES: [
        { name: 'a_position', size: 2, type: FLOAT },
        { name: 'a_size', size: 1, type: FLOAT },
        { name: 'a_color', size: 4, type: UNSIGNED_BYTE, normalized: true },
        { name: 'a_id', size: 4, type: UNSIGNED_BYTE, normalized: true },
      ],
      CONSTANT_ATTRIBUTES: [{ name: 'a_angle', size: 1, type: FLOAT }],
      CONSTANT_DATA: [[ANGLE_1], [ANGLE_2], [ANGLE_3]],
    };
  }

  processVisibleItem(nodeIndex: number, startIndex: number, data: NodeDisplayData) {
    const array = this.array;
    const color = floatColor(data.color);
    array[startIndex++] = data.x;
    array[startIndex++] = data.y;
    array[startIndex++] = data.size;
    array[startIndex++] = color;
    array[startIndex++] = nodeIndex;
  }

  setUniforms(params: RenderParams, { gl, uniformLocations }: ProgramUniforms<(typeof UNIFORMS)[number]>) {
    const { u_sizeRatio, u_correctionRatio, u_matrix } = uniformLocations;
    gl.uniform1f(u_correctionRatio, params.correctionRatio);
    gl.uniform1f(u_sizeRatio, params.sizeRatio);
    gl.uniformMatrix3fv(u_matrix, false, params.matrix);
  }
}
