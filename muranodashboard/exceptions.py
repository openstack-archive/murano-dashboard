
from muranoclient.common import exceptions as muranoclient_exc


RECOVERABLE = (muranoclient_exc.HTTPException,
               muranoclient_exc.HTTPForbidden,
               muranoclient_exc.CommunicationError)

NOT_FOUND = (muranoclient_exc.NotFound,
             muranoclient_exc.EndpointNotFound)

UNAUTHORIZED = (muranoclient_exc.HTTPUnauthorized,)
