import { HEX_COLOUR_REGEX } from "@/schemas/palette";

/** A colour word key under `create.coverIdeas.colorNames`. */
export type ColourName =
  | "black"
  | "charcoal"
  | "gray"
  | "white"
  | "red"
  | "orange"
  | "yellow"
  | "green"
  | "teal"
  | "blue"
  | "indigo"
  | "purple"
  | "pink";

/** Upper hue bound (degrees, exclusive) of each named hue, in hue order. */
const HUE_LIMITS: Readonly<Record<string, number>> = {
  red: 15,
  orange: 45,
  yellow: 70,
  green: 160,
  teal: 195,
  blue: 230,
  indigo: 260,
  purple: 300,
  pink: 340,
};
const FULL_TURN = 360;
const DARKEST = 0.08;
const DARK_GREY = 0.3;
const LIGHTEST = 0.92;
const GREY_SATURATION = 0.15;
const CHANNEL_MAX = 255;
const HEX_RADIX = 16;
const DEGREES = 60;
const GREEN_OFFSET = 2;
const BLUE_OFFSET = 4;
const RED_AT = 1;
const GREEN_AT = 3;
const BLUE_AT = 5;
const CHANNEL_DIGITS = 2;

function channel(hex: string, at: number): number {
  return (
    Number.parseInt(hex.slice(at, at + CHANNEL_DIGITS), HEX_RADIX) / CHANNEL_MAX
  );
}

/** The hue in degrees of an RGB colour whose channel spread ``delta`` is > 0. */
function hue([r, g, b]: readonly number[], delta: number): number {
  const red = r ?? 0;
  const green = g ?? 0;
  const blue = b ?? 0;
  const max = Math.max(red, green, blue);
  if (max === red)
    return (DEGREES * ((green - blue) / delta) + FULL_TURN) % FULL_TURN;
  if (max === green) return DEGREES * ((blue - red) / delta + GREEN_OFFSET);
  return DEGREES * ((red - green) / delta + BLUE_OFFSET);
}

/** The nearest colour word of a ``#rrggbb`` colour ("gray" if invalid). */
export function colourName(hex: string): ColourName {
  if (!HEX_COLOUR_REGEX.test(hex)) return "gray";
  const rgb = [
    channel(hex, RED_AT),
    channel(hex, GREEN_AT),
    channel(hex, BLUE_AT),
  ];
  const max = Math.max(...rgb);
  const min = Math.min(...rgb);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (lightness < DARKEST) return "black";
  if (lightness > LIGHTEST) return "white";
  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  if (saturation < GREY_SATURATION) {
    return lightness < DARK_GREY ? "charcoal" : "gray";
  }
  const degrees = hue(rgb, delta);
  const match = Object.entries(HUE_LIMITS).find(([, limit]) => degrees < limit);
  return (match?.[0] ?? "red") as ColourName;
}
