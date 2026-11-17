import Swal, { type SweetAlertOptions, type SweetAlertResult } from 'sweetalert2';

export const alert = (options: SweetAlertOptions): Promise<SweetAlertResult> => {
  return Swal.fire(options);
};

export default alert;

