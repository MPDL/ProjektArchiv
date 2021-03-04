import React, { Fragment } from 'react';
import { gettext, siteRoot } from '../utils/constants';
import ModalPortal from './modal-portal';
import AboutDialog from './dialog/about-dialog';

class SideNavFooter extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isAboutDialogShow: false,
      collapsed: true
    };
  }

  onAboutDialogToggle = () => {
    this.setState({isAboutDialogShow: !this.state.isAboutDialogShow});
  }

  onFooterExpandedToggle = () => {
    this.setState({collapsed: !this.state.collapsed});
  }

  render() {
      const elementBodyStyle = {
      maxHeight: this.state.collapsed ? '0' : '30rem',
      borderBottomWidth: this.state.collapsed ? '0' : '1px',
    };
    return (
        <Fragment>
            <div className="side-nav-footer">
                <div id="footer-header">
                  <span aria-hidden="true"
                        className={(this.state.collapsed ? 'keeper-icon-triangle-up' : 'keeper-icon-triangle-down') + ' vam'}
                        onClick={this.onFooterExpandedToggle}/>&nbsp;
                    <a href={siteRoot + 'catalog/'} target="_blank" className="item">{gettext('Project Catalog')}</a>
                    <a href="https://mpdl.zendesk.com/hc/en-us/categories/360001234340-Keeper" target="_blank"
                       className="item">{gettext('Help / Knowledge Base')}</a>
                    <a className="item cursor-pointer last-item" onClick={this.onAboutDialogToggle}>{gettext('About')}</a>
                </div>

                <div id="footer-body" style={elementBodyStyle}>
                    <br/>
                    <div className="row">
                        <div className="left">
                            <h4>What you need to know</h4>
                            <a href="https://keeper.mpdl.mpg.de/f/d17ecbb967/" target="_blank">About Keeper</a><br/>
                            <a href="https://keeper.mpdl.mpg.de/f/1b0bfceac2/" target="_blank">Cared Data
                                Commitment</a><br/>
                            <a href="https://keeper.mpdl.mpg.de/f/f62758e53c/" target="_blank">Terms of Service</a>
                        </div>
                        <div className="right">
                                <h4>Client</h4>
                                <a href="/download_client_program/" target="_blank">Download the Keeper client for Windows, Linux, Mac, Android and iPhone</a>
                        </div>
                    </div>
                    <div className="row">
                        <div className="left">
                            <h4>The software behind Keeper</h4>
                            <a href="https://seafile.com/en/home/" target="_blank">
                                <img className="logo" id="seafile-logo" src="/media/custom/seafile_logo_footer.png"/>&nbsp;© 2020 Seafile
                            </a>
                        </div>
                        <div className="right">
                            <h4>A service by</h4>
                            <a href="https://www.mpdl.mpg.de/" target="_blank">
                                <img className="logo" id="MPDL-logo" src="/media/custom/mpdl.png"/>
                            </a><br/><br/>
                            <a href="mailto:keeper@mpdl.mpg.de" target="_blank">Contact Keeper Support</a><br/>
                            <a href="https://keeper.mpdl.mpg.de/f/17e4e9d648/" target="_blank">Impressum</a><br/>
                            <a href="https://keeper.mpdl.mpg.de/f/bf2c8a977f70428587eb/" target="_blank">Privacy Policy</a>
                        </div>
                    </div>
                </div>
                {this.state.isAboutDialogShow &&
                <ModalPortal>
                    <AboutDialog onCloseAboutDialog={this.onAboutDialogToggle}/>
                </ModalPortal>
                }
            </div>
        </Fragment>
    );
  }
}

export default SideNavFooter;
