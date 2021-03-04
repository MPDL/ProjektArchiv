import React from 'react';
import PropTypes from 'prop-types';
import {Modal, ModalHeader, ModalBody, ModalFooter} from 'reactstrap';
import {gettext} from '../../utils/constants';
import {keeperAPI} from '../../utils/seafile-api';
import {Utils} from '../../utils/utils';
import toaster from '../toast';

const propTypes = {
    repoID: PropTypes.string.isRequired,
    repoName: PropTypes.string.isRequired,
    toggleDialog: PropTypes.func.isRequired,
    hideDialog: PropTypes.func.isRequired
};

class ArchiveLibraryDialog extends React.Component {
    constructor(props) {
        super(props);
    }


    formSubmit = () => {
        this.props.hideDialog();
        const {repoID, repoName} = this.props;
        keeperAPI.archiveLibrary(repoID).then((resp) => {
            toaster.success(resp.data.msg, {duration: 3});
        }).catch((error) => {
            let errorMsg = Utils.getErrorMsg(error);
            toaster.danger(errorMsg, {duration: 3});
        });
    }

    render() {
        const archive_info = gettext("By archiving this library, the current state of everything contained within " +
            "it will be archived on a dedicated archiving system. For more information, please follow the link: " +
            "{archive_info_link} This library can be archived {quota} more times.").replace("{quota}",
            this.props.quota);
        const split = archive_info.split('{archive_info_link}')
        return (
            <Modal isOpen={true} toggle={this.props.hideDialog}>
                <ModalHeader toggle={this.props.hideDialog}>
                    <span>{gettext('Archive {library_name}').replace('{library_name}', '')}</span> <span
                    style={{color: '#57a5b8'}}>{this.props.repoName}</span> </ModalHeader>
                <ModalBody>
                    {split[0]}
                    <a href="https://mpdl.zendesk.com/hc/en-us/articles/360011432700-Archiving"
                       target="_blank">{gettext("Information on Archiving")}</a>.
                    {split[1]}
                </ModalBody>
                <ModalFooter>
                    <button className="btn btn-primary" onClick={this.formSubmit}>{gettext('Archive')}</button>
                </ModalFooter>
            </Modal>
        )
    }
}

ArchiveLibraryDialog.propTypes = propTypes;

export default ArchiveLibraryDialog;
