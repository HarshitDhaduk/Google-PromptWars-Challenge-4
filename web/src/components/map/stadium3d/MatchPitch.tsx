"use client";

/**
 * The "live broadcast": a deterministic match simulation rendered on the 3D
 * pitch. Player and ball motion are pure functions of the accelerated sim
 * clock (no randomness, no network), and the scripted goal events from the
 * match fixture pull the ball to the goal mouth at the right minute.
 */

import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Mesh } from "three";

import {
  makeSimAnchor,
  phaseForWallMinute,
  scoreboardMinute,
  wallMinuteAt,
  type SimAnchor,
} from "../../../lib/format";
import type { Match } from "../../../lib/types";

const PITCH_LENGTH = 105;
const PITCH_WIDTH = 68;
const HALF_X = PITCH_LENGTH / 2;
const HALF_Z = PITCH_WIDTH / 2;

const HOME_COLOR = "#7ec8ff"; // Argentina sky blue
const AWAY_COLOR = "#3a5bdc"; // France royal blue

// 4-3-3, home team attacking +x; the away side is mirrored.
const FORMATION: readonly [number, number][] = [
  [-48, 0],
  [-34, -22],
  [-36, -8],
  [-36, 8],
  [-34, 22],
  [-14, -15],
  [-16, 0],
  [-14, 15],
  [10, -18],
  [14, 0],
  [10, 18],
];

/** Smooth pseudo-random drift around a formation anchor (t in sim seconds). */
function drift(t: number, index: number, keeper: boolean): [number, number] {
  const scale = keeper ? 0.3 : 1;
  const dx = (6 * Math.sin(0.031 * t + index * 2.1) + 3 * Math.sin(0.013 * t + index * 0.7)) * scale;
  const dz = (5 * Math.cos(0.027 * t + index * 1.3) + 3 * Math.sin(0.017 * t + index * 2.9)) * scale;
  return [dx, dz];
}

function ballPath(t: number): [number, number] {
  const x = 30 * Math.sin(0.023 * t) + 15 * Math.sin(0.0078 * t + 2);
  const z = 18 * Math.sin(0.019 * t + 1) + 9 * Math.cos(0.011 * t);
  return [x, z];
}

const clamp = (value: number, limit: number) => Math.max(-limit, Math.min(limit, value));

export function MatchPitch({
  match,
  simTimeIso,
  speed,
}: {
  match: Match;
  simTimeIso: string;
  speed: number;
}) {
  // The anchor pairs a sim timestamp with a real timestamp; it is created
  // lazily inside the frame loop because reading the clock during render
  // would be impure.
  const anchorRef = useRef<SimAnchor | null>(null);
  useEffect(() => {
    anchorRef.current = null;
  }, [simTimeIso, speed, match.kickoff_utc]);

  const homeRefs = useRef<(Mesh | null)[]>([]);
  const awayRefs = useRef<(Mesh | null)[]>([]);
  const ballRef = useRef<Mesh>(null);
  const playersRef = useRef<{ visible: boolean }>({ visible: false });

  useFrame(() => {
    if (anchorRef.current === null) {
      anchorRef.current = makeSimAnchor(simTimeIso, speed, match.kickoff_utc, performance.now());
    }
    const wallMinute = wallMinuteAt(anchorRef.current, performance.now());
    const phase = phaseForWallMinute(wallMinute);
    const playing = phase === "first_half" || phase === "second_half";
    const t = wallMinute * 60;

    playersRef.current.visible = playing;
    homeRefs.current.forEach((mesh, index) => {
      if (!mesh) return;
      mesh.visible = playing;
      if (!playing) return;
      const [ax, az] = FORMATION[index];
      const [dx, dz] = drift(t, index, index === 0);
      mesh.position.set(clamp(ax + dx, HALF_X - 3), 1.7, clamp(az + dz, HALF_Z - 3));
    });
    awayRefs.current.forEach((mesh, index) => {
      if (!mesh) return;
      mesh.visible = playing;
      if (!playing) return;
      const [ax, az] = FORMATION[index];
      const [dx, dz] = drift(t + 400, index, index === 0);
      mesh.position.set(clamp(-ax - dx, HALF_X - 3), 1.7, clamp(az + dz, HALF_Z - 3));
    });

    const ball = ballRef.current;
    if (ball) {
      ball.visible = playing;
      if (playing) {
        const minute = scoreboardMinute(wallMinute);
        const goal = match.events.find(
          (event) =>
            event.type === "goal" && minute !== null && Math.abs(minute - event.minute) < 0.8,
        );
        if (goal) {
          // Home attacks +x, so a home goal lands in the +x goal mouth.
          ball.position.set(goal.team === match.home_code ? HALF_X - 1 : 1 - HALF_X, 0.9, 0);
        } else {
          const [bx, bz] = ballPath(t);
          ball.position.set(clamp(bx, HALF_X - 2), 0.9, clamp(bz, HALF_Z - 2));
        }
      }
    }
  });

  return (
    <group>
      {/* Turf and markings */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.3, 0]}>
        <planeGeometry args={[PITCH_LENGTH, PITCH_WIDTH]} />
        <meshStandardMaterial color="#0d6b41" roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.42, 0]}>
        <ringGeometry args={[8.6, 9.2, 40]} />
        <meshBasicMaterial color="#e8f2ec" />
      </mesh>
      <mesh position={[0, 0.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[0.6, PITCH_WIDTH]} />
        <meshBasicMaterial color="#e8f2ec" />
      </mesh>
      {[-1, 1].map((side) => (
        <group key={side}>
          {/* Goal frame */}
          <mesh position={[side * (HALF_X + 0.8), 1.6, 0]}>
            <boxGeometry args={[1.2, 3.2, 9]} />
            <meshStandardMaterial color="#eef3fb" />
          </mesh>
          {/* Penalty box line */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[side * (HALF_X - 8), 0.42, 0]}>
            <planeGeometry args={[0.5, 32]} />
            <meshBasicMaterial color="#e8f2ec" />
          </mesh>
        </group>
      ))}

      {/* Players */}
      {FORMATION.map((_, index) => (
        <mesh
          key={`home-${index}`}
          ref={(mesh) => {
            homeRefs.current[index] = mesh;
          }}
          visible={false}
        >
          <capsuleGeometry args={[1.1, 2, 4, 8]} />
          <meshStandardMaterial color={HOME_COLOR} />
        </mesh>
      ))}
      {FORMATION.map((_, index) => (
        <mesh
          key={`away-${index}`}
          ref={(mesh) => {
            awayRefs.current[index] = mesh;
          }}
          visible={false}
        >
          <capsuleGeometry args={[1.1, 2, 4, 8]} />
          <meshStandardMaterial color={AWAY_COLOR} />
        </mesh>
      ))}

      {/* Ball */}
      <mesh ref={ballRef} visible={false}>
        <sphereGeometry args={[0.9, 16, 16]} />
        <meshStandardMaterial color="#f5f7fa" />
      </mesh>
    </group>
  );
}
