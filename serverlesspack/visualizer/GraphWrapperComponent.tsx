import * as React from 'react';
import * as ReactDOM from 'react-dom';
import * as d3 from "d3";

import Dropzone from 'react-dropzone';
import BarChart from "./NetworkDirectedGraphComponent";
import {filesArrayToFilesMap} from "../../../inoft_vocal_engine/web_interface/static/applications/data-lake/DriveApplication/utils";


export interface GraphWrapperProps {
}

export interface GraphWrapperState {
    size?: {
        width: number;
        height: number;
    };
    data?: any[];
}


export default class GraphWrapperComponent extends React.Component<GraphWrapperProps, GraphWrapperState> {
    private readonly containerRef: React.RefObject<HTMLDivElement>;

    constructor(props: GraphWrapperProps) {
        super(props);
        this.state = {
        };
        this.containerRef = React.createRef();

        this.onDropFiles = this.onDropFiles.bind(this);
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

    private onDropFiles(acceptedFiles: File[]) {
        acceptedFiles.forEach((file) => {
            const reader = new FileReader();
            reader.onabort = () => console.log('file reading was aborted');
            reader.onerror = () => console.log('file reading has failed');
            reader.onload = () => {
                // Do whatever you want with the file contents
                const resultString = reader.result as string;
                const resultJson = JSON.parse(resultString);
                this.setState({data: resultJson});
            }
            reader.readAsText(file);
        });
    }

    render() {
        const id = 'greatId';
        return (
            <Dropzone onDrop={this.onDropFiles}>
                {({getRootProps, getInputProps}) => (
                    <div {...getRootProps()} tabIndex={undefined} style={{width: "100%", height: "100%"}}>
                        <div ref={this.containerRef} style={{width: "100%", height: "100%"}}>
                            <div id={id} className='container' />
                            {this.state.data !== undefined && this.state.size !== undefined ?
                                <BarChart id={id} data={this.state.data} width={this.state.size.width} height={this.state.size.height} /> : null
                            }
                        </div>
                    </div>
                )}
            </Dropzone>
        );
    }
}


document.addEventListener('DOMContentLoaded', () => {
    ReactDOM.render(<GraphWrapperComponent />, document.getElementById('application-container'));
});