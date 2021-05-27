import * as React from 'react';
import * as _ from 'lodash';
import * as d3 from 'd3';
import {Point, SourceLinkItem, ClientNodeItem, ClientLinkItem} from "./models";


export interface NetworkDirectedGraphProps {
    id: string;
    data: SourceLinkItem[];
    width: number;
    height: number;
}

export interface NetworkDirectedGraphState {

}


export default class BarChart extends React.Component<NetworkDirectedGraphProps, NetworkDirectedGraphState> {
    private links: ClientLinkItem[];
    private nodes: { [key: string]: ClientNodeItem };
    private nodesValues: ClientNodeItem[];
    private readonly nodeRadius: number;
    private readonly forcePadding: number;
    private readonly targetDistanceUnitLength: number;

    private simulation: d3.Simulation<d3.SimulationNodeDatum, undefined>;
    private linkPath: d3.Selection<SVGPathElement, ClientLinkItem, SVGGElement, unknown>;
    private linkLabel: d3.Selection<SVGTextElement, ClientLinkItem, SVGGElement, unknown>;
    private nodeCircle: d3.Selection<SVGCircleElement, any, SVGGElement, unknown>;
    private nodeLabel: d3.Selection<SVGTextElement, any, SVGGElement, unknown>;
    private svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, any>;

    constructor(props: NetworkDirectedGraphProps) {
        super(props);

        this.nodeRadius = 25;
        this.forcePadding = this.nodeRadius + 10;
        this.targetDistanceUnitLength = this.nodeRadius / 4;

        [this.links, this.nodes] = this.linksNodes();
        this.nodesValues = _.map(this.nodes);
        this.simulation = this.createSimulation();

        const chartContainer = d3.select(`#${this.props.id}`);

        this.svg = chartContainer
            .append("svg")
            .attr("width", this.props.width)
            .attr("height", this.props.height);

        const dataDependantElements = this.createDataDependantElements();
        this.linkPath = dataDependantElements.linkPath;
        this.linkLabel = dataDependantElements.linkLabel;
        this.nodeCircle = dataDependantElements.nodeCircle;
        this.nodeLabel = dataDependantElements.nodeLabel;

        this.ticked = this.ticked.bind(this);
        this.transform = this.transform.bind(this);

    }

    private linksNodes(): [ ClientLinkItem[], { [key: string]: ClientNodeItem } ] {
        const nodes: { [key: string]: ClientNodeItem } = {};

        // Compute the distinct nodes from the links.
        const links: ClientLinkItem[] = _.map(this.props.data, (linkItem: SourceLinkItem) => ({
            targetDistance: 0,
            type: linkItem.type,
            offsetX: 0, offsetY: 0,
            source: nodes[linkItem.source] || (nodes[linkItem.source] = {name: linkItem.source}),
            target: nodes[linkItem.target] || (nodes[linkItem.target] = {name: linkItem.target})
        }));

        // Compute targetDistance for each link
        for (let i = 0; i < links.length; i++) {
            if (links[i].targetDistance === -1) continue;
            for (let j = i + 1; j < links.length; j++) {
                if (links[j].targetDistance === -1) continue;
                if (
                    links[i].target === links[j].source &&
                    links[i].source === links[j].target
                ) {
                    links[i].targetDistance = 1;
                    links[j].targetDistance = -1;
                }
            }
        }
        return [links, nodes];
    }

    private createDataDependantElements() {
        // Per-type markers, as they don't inherit styles.
        this.svg
            .append("defs")
            .selectAll("marker")
            .data(["request-rejected", "request-accepted", "response"])
            .enter()
            .append("marker")
            .attr("id", d => d)
            .attr("markerWidth", 8)
            .attr("markerHeight", 8)
            .attr("refX", this.nodeRadius + 8)
            .attr("refY", 4)
            .attr("orient", "auto")
            .attr("markerUnits", "userSpaceOnUse")
            .append("path")
            .attr("d", "M0,0 L0,8 L8,4 z");

        const linkPath = this.svg
            .append("g")
            .selectAll("path")
            .data(this.links)
            .enter()
            .append("path")
            .attr("id", (d, i) => `link-${i}`)
            .attr("class", d => `link ${d.type}`)
            .attr("marker-end", d => `url(#${d.type})`);

        const linkLabel = this.svg
            .append("g")
            .selectAll("text")
            .data(this.links)
            .enter()
            .append("text")
            .attr("class", "link-label")
            .attr("text-anchor", "middle")
            .attr("dy", "0.31em");
        linkLabel
            .append("textPath")
            .attr("href", (d, i) => `#link-${i}`)
            .attr("startOffset", "50%")
            .text((d: ClientLinkItem) => d.type);

        const nodeCircle = this.svg
            .append("g")
            .selectAll("circle")
            .data(this.nodesValues)
            .enter()
            .append("circle")
            .attr("r", this.nodeRadius)
            .call(d3.drag()
                .on("start", this.dragstarted.bind(this))
                .on("drag", this.dragged.bind(this))
                .on("end", this.dragended.bind(this))
            );

        const nodeLabel = this.svg
            .append("g")
            .selectAll("text")
            .data(this.nodesValues)
            .enter()
            .append("text")
            .attr("class", "node-label")
            .attr("y", ".31em")
            .attr("text-anchor", "middle")
            .text((d: ClientNodeItem) => d.name);

        return {linkPath, linkLabel, nodeCircle, nodeLabel};
    }

    private createSimulation() {
        return d3
            .forceSimulation()
            .force("link", d3
                .forceLink()
                .id((d) => d.name)
                .distance(200)
                .links(this.links)
            )
            .force("collide", d3
                .forceCollide()
                .radius(this.nodeRadius + 0.5)
                .iterations(4)
            )
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(this.props.width / 2, this.props.height / 2))
            .on("tick", this.ticked.bind(this))
            .nodes(this.nodesValues);
    }

    private resize() {
        this.simulation?.stop();
        this.simulation = this.createSimulation();
        this.svg
            .attr("width", this.props.width)
            .attr("height", this.props.height);
    }

    componentDidUpdate(prevProps: Readonly<NetworkDirectedGraphProps>, prevState: Readonly<NetworkDirectedGraphState>, snapshot?: any): void {
        if (this.props.width !== prevProps.width || this.props.height !== prevProps.height) {
            this.resize();
        }
        if (this.props.data !== prevProps.data) {
            console.log("data changed");
            this.linkPath.remove();
            this.linkLabel.remove();
            this.nodeCircle.remove();
            this.nodeLabel.remove();

            [this.links, this.nodes] = this.linksNodes();
            this.nodesValues = _.map(this.nodes);

            const dataDependantElements = this.createDataDependantElements();
            this.linkPath = dataDependantElements.linkPath;
            this.linkLabel = dataDependantElements.linkLabel;
            this.nodeCircle = dataDependantElements.nodeCircle;
            this.nodeLabel = dataDependantElements.nodeLabel;
            this.createSimulation();
        }
    }

    // https://bl.ocks.org/ramtob/3658a11845a89c4742d62d32afce3160
    /**
     * @param {number} targetDistance
     * @param {x,y} point0
     * @param {x,y} point1, two points that define a line segmemt
     * @returns
     * a translation {dx,dy} from the given line segment, such that the distance
     * between the given line segment and the translated line segment equals
     * targetDistance
     */
    private calcTranslation(targetDistance: number, point0: Point, point1: Point) {
        const x1_x0 = point1.x - point0.x;
        const y1_y0 = point1.y - point0.y;

        const [x2_x0, y2_y0] = y1_y0 === 0 ? [0, targetDistance] : (() => {
            const angle = Math.atan(x1_x0 / y1_y0);
            const x2_x0 = -targetDistance * Math.cos(angle);
            const y2_y0 = targetDistance * Math.sin(angle);
            return [x2_x0, y2_y0];
        })();
        return {dx: x2_x0, dy: y2_y0};
    }

    // Use elliptical arc path segments to doubly-encode directionality.
    private ticked() {
        this.linkPath
            .attr("d", (link: ClientLinkItem) => `M${link.source.x},${link.source.y} L${link.target.x},${link.target.y}`)
            .attr("transform", (link: ClientLinkItem) => {
                const translation = this.calcTranslation(
                    link.targetDistance * this.targetDistanceUnitLength,
                    link.source,
                    link.target
                );
                link.offsetX = translation.dx;
                link.offsetY = translation.dy;
                return `translate (${link.offsetX}, ${link.offsetY})`;
            });

        this.linkLabel.attr("transform", (link: ClientLinkItem) => {
            if ((link.target.x as number) < (link.source.x as number)) {
                const cor1: number = (((link.source.x as number) + (link.target.x as number)) / 2 + link.offsetX);
                const cor2: number = (((link.source.y as number) + (link.target.y as number)) / 2 + link.offsetY);
                return `rotate(180,${cor1},${cor2})`;
            } else {
                return "rotate(0)";
            }
        });
        this.nodeCircle.attr("transform", this.transform);
        this.nodeLabel.attr("transform", this.transform);
    }

    private transform(node: ClientNodeItem) {
        node.x =
            (node.x as number) <= this.forcePadding
                ? this.forcePadding
                : (node.x as number) >= this.props.width - this.forcePadding
                ? this.props.width - this.forcePadding
                : (node.x as number);
        node.y =
            (node.y as number) <= this.forcePadding
                ? this.forcePadding
                : (node.y as number) >= this.props.height - this.forcePadding
                ? this.props.height - this.forcePadding
                : (node.y as number);
        return `translate(${node.x},${node.y})`;
    }

    private dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = event.x;
        d.fy = event.y;
    }

    private dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    private dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    render() {
        return null;
    }
}
