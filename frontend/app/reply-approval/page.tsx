import { redirect } from "next/navigation";

export default function ReplyApprovalRedirect() {
  redirect("/comment-inbox");
}
