import * as React from 'react';
import * as ReactDOM from 'react-dom';
import * as d3 from 'd3';


export interface NetworkDirectedGraphProps {

}

export interface NetworkDirectedGraphState {

}


export default class BarChart extends React.Component<NetworkDirectedGraphProps, NetworkDirectedGraphState> {
    private readonly width: number;
    private readonly height: number;
    private readonly nodeRadius: number;
    private readonly forcePadding: number;
    private readonly targetDistanceUnitLength: number;
    private linkPath?: d3.Selection<SVGPathElement, unknown, SVGGElement, unknown>;
    private linkLabel?: d3.Selection<SVGTextElement, unknown, SVGGElement, unknown>;

    constructor(props: NetworkDirectedGraphProps) {
        super(props);
        this.width = 1200;
        this.height = 800;
        this.nodeRadius = 25;
        this.forcePadding = this.nodeRadius + 10;
        this.targetDistanceUnitLength = this.nodeRadius / 4;
    }

    componentDidMount() {
      d3.json("input_graph_data.json").then((data) => {
          this.update(data)
      });
      this.drawChart();
    }

    update(links: d3Link[]) {
        const nodes: { [key: string]: any } = {};

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

        ////////////////////////////////////////////////////////////
        //// Initial Setup /////////////////////////////////////////
        ////////////////////////////////////////////////////////////

        const simulation = d3
            .forceSimulation()
            .force(
                "link",
                d3.forceLink()
                    .id((d) => (d).name)
                    .distance(200)
                    .links(links)
            )
            .force(
                "collide",
                d3.forceCollide()
                    .radius(this.nodeRadius + 0.5)
                    .iterations(4)
            )
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2))
            .on("tick", this.ticked)
            .nodes(d3.values(nodes));

        ////////////////////////////////////////////////////////////
        //// Render Chart //////////////////////////////////////////
        ////////////////////////////////////////////////////////////

        const chartContainer = d3.select(".chart-container");

        const svg = chartContainer
            .append("svg")
            .attr("width", this.width)
            .attr("height", this.height);

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
            .attr("id", (d, i: number) => `link-${i}`)
            .attr("class", (d) => `link ${d.type}`)
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
            .text((d) => (d as d3Link).type);

        const nodeCircle = svg
            .append("g")
            .selectAll("circle")
            .data(d3.values(nodes))
            .enter()
            .append("circle")
            .attr("r", this.nodeRadius)
            .call(
                d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended)
            );

        const nodeLabel = svg
            .append("g")
            .selectAll("text")
            .data(d3.values(nodes))
            .enter()
            .append("text")
            .attr("class", "node-label")
            .attr("y", ".31em")
            .attr("text-anchor", "middle")
            .text(function (d) {
                return d.name;
            });
    }

    // Use elliptical arc path segments to doubly-encode directionality.
    ticked() {
        if (this.linkPath !== undefined && this.linkLabel !== undefined) {
            this.linkPath
                .attr("d", d => `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`)
                .attr("transform", d => {
                    const translation = this.calcTranslation(
                        d.targetDistance * this.targetDistanceUnitLength,
                        d.source,
                        d.target
                    );
                    d.offsetX = translation.dx;
                    d.offsetY = translation.dy;
                    return `translate (${d.offsetX}, ${d.offsetY})`;
                });
            this.linkLabel.attr("transform", d => {
                if (d.target.x < d.source.x) {
                    return (
                        "rotate(180," +
                        ((d.source.x + d.target.x) / 2 + d.offsetX) +
                        "," +
                        ((d.source.y + d.target.y) / 2 + d.offsetY) +
                        ")"
                    );
                } else {
                    return "rotate(0)";
                }
            });
            nodeCircle.attr("transform", transform);
            nodeLabel.attr("transform", transform);
        }
    }

    transform(d) {
        d.x =
        d.x <= this.forcePadding
            ? this.forcePadding
            : d.x >= this.width - this.forcePadding
            ? this.width - this.forcePadding
            : d.x;
        d.y =
        d.y <= this.forcePadding
            ? this.forcePadding
            : d.y >= this.height - this.forcePadding
            ? this.height - this.forcePadding
            : d.y;
        return "translate(" + d.x + "," + d.y + ")";
    }

    dragstarted(d) {
        if (!d3.event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(d) {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
    }

    dragended(d) {
        if (!d3.event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
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
    calcTranslation(targetDistance: number, point0, point1) {
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

    drawChart() {
        const data = [12, 5, 6, 6, 9, 10];

        const svg = d3.select("body")
            .append("svg")
            .attr("width", w)
            .attr("height", h)
            .style("margin-left", 100);

        svg.selectAll("rect")
            .data(data)
            .enter()
            .append("rect")
            .attr("x", (d, i) => i * 70)
            .attr("y", (d, i) => h - 10 * d)
            .attr("width", 65)
            .attr("height", (d, i) => d * 10)
            .attr("fill", "green")
    }

    render() {
        return <div id={"#" + this.props.id}></div>
    }
}

document.addEventListener('DOMContentLoaded', () => {
    ReactDOM.render(<BarChart />, document.getElementById('application-container'));
});