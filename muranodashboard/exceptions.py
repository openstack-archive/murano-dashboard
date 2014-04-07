from horizon import exceptions
from muranoclient.common import exceptions as muranoclient_exc


exceptions.RECOVERABLE += (muranoclient_exc.HTTPException,
                           muranoclient_exc.HTTPForbidden,
                           muranoclient_exc.CommunicationError)

exceptions.NOT_FOUND += (muranoclient_exc.NotFound,
                         muranoclient_exc.EndpointNotFound)

exceptions.UNAUTHORIZED += (muranoclient_exc.HTTPUnauthorized,)
