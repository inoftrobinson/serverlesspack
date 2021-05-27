import * as React from 'react';
import * as ReactDOM from 'react-dom';
import * as _ from 'lodash';
import * as d3 from 'd3';
import {Point, d3Link} from "./models";


export interface NetworkDirectedGraphProps {
    id: string;
    data: any[];
    width: number;
    height: number;
}

export interface NetworkDirectedGraphState {

}


export default class BarChart extends React.Component<NetworkDirectedGraphProps, NetworkDirectedGraphState> {
    private readonly nodeRadius: number;
    private readonly forcePadding: number;
    private readonly targetDistanceUnitLength: number;
    private linkPath: d3.Selection<SVGPathElement, unknown, SVGGElement, unknown>;
    private linkLabel: d3.Selection<SVGTextElement, unknown, SVGGElement, unknown>;
    private simulation: d3.Simulation<d3.SimulationNodeDatum, undefined>;
    private nodeCircle: d3.Selection<SVGCircleElement, any, SVGGElement, unknown>;
    private nodeLabel: d3.Selection<SVGTextElement, any, SVGGElement, unknown>;
    private svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, any>;
    private links: any[];
    private nodes: {};

    constructor(props: NetworkDirectedGraphProps) {
        super(props);

        this.nodeRadius = 25;
        this.forcePadding = this.nodeRadius + 10;
        this.targetDistanceUnitLength = this.nodeRadius / 4;

        const [links, nodes] = this.linksNodes();
        this.links = links;
        this.nodes = nodes;
        this.simulation = this.createSimulation();

        const chartContainer = d3.select(`#${this.props.id}`);

        const svg = chartContainer
            .append("svg")
            .attr("width", this.props.width)
            .attr("height", this.props.height);
        this.svg = svg;

        this.ticked = this.ticked.bind(this);
        this.transform = this.transform.bind(this);

        // Per-type markers, as they don't inherit styles.
        svg
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

        this.linkPath = svg
            .append("g")
            .selectAll("path")
            .data(links)
            .enter()
            .append("path")
            .attr("id", (d, i) => `link-${i}`)
            .attr("class", d => `link ${d.type}`)
            .attr("marker-end", d => `url(#${d.type})`);

        this.linkLabel = svg
            .append("g")
            .selectAll("text")
            .data(links)
            .enter()
            .append("text")
            .attr("class", "link-label")
            .attr("text-anchor", "middle")
            .attr("dy", "0.31em");
        this.linkLabel
            .append("textPath")
            .attr("href", (d, i) => `#link-${i}`)
            .attr("startOffset", "50%")
            .text(d => d.type);

        this.nodeCircle = svg
            .append("g")
            .selectAll("circle")
            .data(_.values(nodes))
            .enter()
            .append("circle")
            .attr("r", this.nodeRadius)
            .call(d3.drag()
                .on("start", this.dragstarted.bind(this))
                .on("drag", this.dragged.bind(this))
                .on("end", this.dragended.bind(this))
            );

        this.nodeLabel = svg
            .append("g")
            .selectAll("text")
            .data(_.values(nodes))
            .enter()
            .append("text")
            .attr("class", "node-label")
            .attr("y", ".31em")
            .attr("text-anchor", "middle")
            .text((d) => d.name);

    }

    private linksNodes(): [ any[], {} ] {
        const links = this.props.data;
        const nodes = {};

        // Compute the distinct nodes from the links.
        links.forEach((link) => {
            link.source = nodes[link.source] || (nodes[link.source] = {name: link.source});
            link.target = nodes[link.target] || (nodes[link.target] = {name: link.target});
        });

        // Compute targetDistance for each link
        for (let i = 0; i < links.length; i++) {
            if (links[i].targetDistance === -1) continue;
            links[i].targetDistance = 0;
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

    private resize() {
        this.simulation?.stop();
        this.simulation = this.createSimulation();
        this.svg
            .attr("width", this.props.width)
            .attr("height", this.props.height);
    }

    componentDidUpdate(prevProps: Readonly<NetworkDirectedGraphProps>, prevState: Readonly<NetworkDirectedGraphState>, snapshot?: any): void {
        if (this.props.width !== prevProps.width || this.props.height !== prevProps.height) {
            console.log("should resize");
            this.resize();
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
            .nodes(_.values(this.nodes));
    }

    // Use elliptical arc path segments to doubly-encode directionality.
    private ticked() {
        this.linkPath
            .attr("d", (d) => `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`)
            .attr("transform", (d) => {
                const translation = this.calcTranslation(
                    d.targetDistance * this.targetDistanceUnitLength,
                    d.source,
                    d.target
                );
                d.offsetX = translation.dx;
                d.offsetY = translation.dy;
                return `translate (${d.offsetX}, ${d.offsetY})`;
            });

        this.linkLabel.attr("transform", (d) => {
            if (d.target.x < d.source.x) {
                const cor1: number = ((d.source.x + d.target.x) / 2 + d.offsetX);
                const cor2: number = ((d.source.y + d.target.y) / 2 + d.offsetY);
                return `rotate(180,${cor1},${cor2})`;
            } else {
                return "rotate(0)";
            }
        });
        this.nodeCircle.attr("transform", this.transform);
        this.nodeLabel.attr("transform", this.transform);
    }

    private transform(d) {
        d.x =
            d.x <= this.forcePadding
                ? this.forcePadding
                : d.x >= this.props.width - this.forcePadding
                ? this.props.width - this.forcePadding
                : d.x;
        d.y =
            d.y <= this.forcePadding
                ? this.forcePadding
                : d.y >= this.props.height - this.forcePadding
                ? this.props.height - this.forcePadding
                : d.y;
        return `translate(${d.x},${d.y})`;
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

    update(links: any[]) {
        console.log("CheckPt:update");
        console.log(links);



        ////////////////////////////////////////////////////////////
        //// Initial Setup /////////////////////////////////////////
        ////////////////////////////////////////////////////////////
        const width = this.props.width;
        const height = this.props.height;

        const nodeRadius = 25;

        const forcePadding = nodeRadius + 10;
        const targetDistanceUnitLength = nodeRadius / 4;

        // const simulation = this.createSimulation();
        // this.simulation = simulation;

        ////////////////////////////////////////////////////////////
        //// Render Chart //////////////////////////////////////////
        ////////////////////////////////////////////////////////////


    }

    render() {
        return null;
    }
}
