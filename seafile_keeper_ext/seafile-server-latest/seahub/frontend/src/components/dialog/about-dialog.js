import React from 'react';
import PropTypes from 'prop-types';
import { Modal, ModalBody } from 'reactstrap';
import { gettext, lang, mediaUrl, logoPath, logoWidth, logoHeight, siteTitle, seafileVersion } from '../../utils/constants';

const propTypes = {
  onCloseAboutDialog: PropTypes.func.isRequired,
};

class AboutDialog extends React.Component {

  toggle = () => {
    this.props.onCloseAboutDialog();
  }

  render() {

    return (
      <Modal isOpen={true} toggle={this.toggle}>
        <ModalBody>
          <button type="button" className="close" onClick={this.toggle}><span aria-hidden="true">×</span></button>
          <div className="about-content">
            <p><img src={mediaUrl + logoPath} height={logoHeight} width={logoWidth} title={siteTitle} alt="logo" /></p>
            <p>{gettext('Server Version: ')}{seafileVersion}<br />© 2020 {gettext('KEEPER')}</p>
          </div>
        </ModalBody>
      </Modal>
    );
  }
}

AboutDialog.propTypes = propTypes;

export default AboutDialog;
