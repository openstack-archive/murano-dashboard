from horizon import exceptions
from muranoclient.common import exceptions as muranoclient_exc
from metadataclient.common import exceptions as metadataclient_exc


exceptions.RECOVERABLE += (muranoclient_exc.HTTPException,
                           muranoclient_exc.HTTPForbidden,
                           muranoclient_exc.CommunicationError,
                           metadataclient_exc.HTTPException,
                           metadataclient_exc.HTTPForbidden,
                           metadataclient_exc.CommunicationError,)

exceptions.NOT_FOUND += (muranoclient_exc.NotFound,
                         muranoclient_exc.EndpointNotFound,
                         metadataclient_exc.NotFound,
                         metadataclient_exc.EndpointNotFound,)

exceptions.UNAUTHORIZED += (muranoclient_exc.HTTPUnauthorized,
                            metadataclient_exc.HTTPUnauthorized,)
