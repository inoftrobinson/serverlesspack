export interface Point {
    x: number;
    y: number;
}

export interface SourceLinkItem {
    source: string;
    target: string;
    type: string;
}

export interface ClientLinkItem {
    source: ClientNodeItem;
    target: ClientNodeItem;
    type: string;
    targetDistance: number;
    offsetX: number;
    offsetY: number;
}

export interface ClientNodeItem {
    name: string;
    x?: number;
    y?: number;
}