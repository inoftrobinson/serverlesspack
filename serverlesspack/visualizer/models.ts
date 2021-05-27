export type d3Link = {
    type: string;
    // source: { name: string },
    source: string,
    // target: { name: string },
    target: string,
    targetDistance: number;
};

export type d3ClientLink = {
    source: { name: string },
    target: { name: string },
    targetDistance: number;
}

export interface Point {
    x: number;
    y: number;
}