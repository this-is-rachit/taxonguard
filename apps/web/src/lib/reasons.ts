// Maps engine reason codes to short, human labels for the review screen. Keeping
// this in one place keeps the copy consistent across the list, the badges, and
// the detail panel.

export interface ReasonMeta {
  label: string;
  description: string;
}

export const REASON_META: Record<string, ReasonMeta> = {
  realm_mismatch: {
    label: "Land/sea mismatch",
    description: "Recorded on the wrong side of the land or sea boundary.",
  },
  zero_coordinates: {
    label: "Null island",
    description: "Coordinates are exactly zero.",
  },
  equal_coordinates: {
    label: "Equal coordinates",
    description: "Latitude and longitude are identical.",
  },
  gridded_coordinates: {
    label: "Grid centroid",
    description: "Coordinates fall on whole degrees.",
  },
  institution_coordinates: {
    label: "Institution point",
    description: "Coordinates match a known institution.",
  },
  environmental_outlier: {
    label: "Climate outlier",
    description: "Local climate is far outside the usual range.",
  },
};

export function reasonLabel(code: string): string {
  return REASON_META[code]?.label ?? code;
}
