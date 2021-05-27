import * as React from 'react';
import * as ReactDOM from 'react-dom';
import BarChart from "./NetworkDirectedGraphComponent";
import * as d3 from "d3";


export interface GraphWrapperProps {
}

export interface GraphWrapperState {
    size?: {
        width: number;
        height: number;
    };
    data: any[];
}


export default class GraphWrapperComponent extends React.Component<GraphWrapperProps, GraphWrapperState> {
    private readonly containerRef: React.RefObject<HTMLDivElement>;

    constructor(props: GraphWrapperProps) {
        super(props);
        this.state = {
        };
        this.containerRef = React.createRef();
        window.addEventListener('resize', this.setSize.bind(this));
    }

    setSize() {
        const containerElement: HTMLDivElement | null = this.containerRef.current;
        if (containerElement != null) {
            this.setState({size: {
                width: containerElement.clientWidth,
                height: containerElement.clientHeight
            }});
        }
    }

    componentDidMount() {
        this.setSize();
        d3.json("dist/traces.json").then((data) => {
            this.setState({data});
        });
    }

    render() {
        const id = 'greatId';
        return (
            <div ref={this.containerRef} style={{width: "100%", height: "100%"}}>
                <div id={id} className='container' />
                {this.state.data !== undefined && this.state.size !== undefined ?
                    <BarChart id={id} data={this.state.data} width={this.state.size.width} height={this.state.size.height} /> : null
                }
            </div>
        );
    }
}


document.addEventListener('DOMContentLoaded', () => {
    ReactDOM.render(<GraphWrapperComponent />, document.getElementById('application-container'));
});