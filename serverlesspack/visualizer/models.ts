type d3Link = {
    type: string;
    // source: { name: string },
    source: string,
    // target: { name: string },
    target: string,
    targetDistance: number;
};

type d3ClientLink = {
    source: { name: string },
    target: { name: string },
    targetDistance: number;
}