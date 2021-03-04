import React, { Component } from 'react';
import PropTypes from 'prop-types';

const propTypes = {
  children: PropTypes.object.isRequired,
};

class MainPanel extends Component {

    componentDidMount() {
        const script = document.createElement("script");
        script.src = "https://static.zdassets.com/ekr/snippet.js?key=32977f9b-455d-428b-8dd5-f4c65aad0daa";
        script.id = "ze-snippet";
        script.async = true;
        document.body.appendChild(script);
    }

    render() {
        return (
            <div className="main-panel o-hidden">
                {this.props.children}
            </div>
        );
    }
}

MainPanel.propTypes = propTypes;

export default MainPanel;
