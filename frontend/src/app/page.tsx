import { redirect } from 'next/navigation';

export default function RootPage() {
  // This function immediately redirects the user to the new path
  redirect('/landing_page');

  // You must still return something, even if the redirect happens immediately
  // This code below is unreachable because the redirect throws an error internally
  return (
    <div>
      Redirecting...
    </div>
  );
}